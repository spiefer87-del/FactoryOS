"""Project purpose regression tests using an isolated in-memory database."""
import runpy
from pathlib import Path
from sqlalchemy import text, inspect

fixture = runpy.run_path(str(Path(__file__).with_name('test_project_workspace.py')))
app = fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.projects.workspace_models import Workspace, Link, ToolPartEvent, WorkTime, Report, Audit
from factoryos.modules.projects.definitions import PROJECT_TYPES
from scripts.upgrade_project_workspace import run_upgrade

with app.app_context():
    admin = db.session.merge(fixture['admin'])
    tool = db.session.merge(fixture['tool'])
    error = db.session.merge(fixture['error'])
    c = fixture['client'](admin)
    sampling = SamplingOrder.query.first()
    sampling.order.tool_no = tool.tool_no
    db.session.commit()

    def create(number, kind, reference='none', **extra):
        return c.post('/projects/create', data=dict(access_csrf='project-test', order_no=number,
            description='Testziel', project_kind=kind, reference_kind=reference, **extra))

    def action(item, op, **extra):
        return c.post(f'/projects/{item.id}/action', data=dict(access_csrf='project-test',
            version=db.session.get(Workspace, item.id).version, op=op, **extra))

    # Every new project requires an explicit valid reason, independent of JS.
    for kind in ('', 'legacy', 'invalid'):
        assert create('INVALID-'+kind, kind).status_code == 422
        assert Order.query.filter_by(order_no='INVALID-'+kind).first() is None
    for kind, config in PROJECT_TYPES.items():
        if kind == 'legacy': continue
        if config['sampling_required']:
            response = create('TYPE-'+kind, kind, 'sampling', sampling_id=sampling.id)
        elif config['tool_required']:
            assert create('NO-TOOL-'+kind, kind).status_code == 422
            response = create('TYPE-'+kind, kind, 'tool', tool_id=tool.id)
        else:
            response = create('TYPE-'+kind, kind)
        assert response.status_code == 303, response.get_data(as_text=True)
        item = Order.query.filter_by(order_no='TYPE-'+kind).one()
        assert db.session.get(Workspace, item.id).project_kind == kind
        assert action(item, 'task_add', title='Nächster Schritt', assignee_id=admin.id).status_code == 303
        page = c.get(f'/projects/{item.id}').get_data(as_text=True)
        assert config['label'] in page
        assert ('Einbau / Ausbau dokumentieren' in page) == config['parts']
        assert ('Wartet auf Ersatzteil' in page) == config['parts']
        assert 'Arbeitszeiten' in page and 'Arbeitsberichte' in page

    assert create('MISSING-SAMPLING', 'sampling_work', 'tool', tool_id=tool.id).status_code == 422
    assert create('BAD-SAMPLING', 'sampling_work', 'sampling', sampling_id='999999').status_code == 422
    assert create('BAD-TOOL', 'tool_repair', 'tool', tool_id='bad').status_code == 422
    assert create('BAD-REFERENCE', 'other', 'bad').status_code == 422
    assert create('TYPE-other', 'other').status_code == 422

    # Selecting sampling derives its tool, creates a link, and retains the source data.
    assert create('PREP-LINK', 'sampling_preparation', 'sampling', sampling_id=sampling.id).status_code == 303
    prep = Order.query.filter_by(order_no='PREP-LINK').one()
    assert prep.tool_no == tool.tool_no
    assert Link.query.filter_by(project_id=prep.id, sampling_id=sampling.id).one()
    assert c.get(f'/projects/sources?project_id={prep.id}&kind=error&q=FM').status_code == 403
    assert action(prep, 'link', kind='error', target_id=error.id).status_code == 422
    assert action(prep, 'part').status_code == 422
    assert ToolPartEvent.query.filter_by(project_id=prep.id).count() == 0
    assert action(prep, 'report', text='Vorbereitung dokumentiert').status_code == 303
    assert action(prep, 'time_start', description='Musterung vorbereiten').status_code == 303
    entry = WorkTime.query.filter_by(project_id=prep.id).one()
    assert action(prep, 'time_stop', time_id=entry.id).status_code == 303

    # No source-reading permission can be bypassed through creation.
    role = Role(name='project-creator-only', active=True)
    db.session.add(role)
    for name in ('projects.view', 'projects.create'):
        role.permissions.append(Permission.query.filter_by(name=name).one())
    creator = User(username='creator-only', password_hash='unused', active=True, role=role)
    db.session.add(creator); db.session.commit()
    limited = fixture['client'](creator)
    page = limited.get('/projects/create').get_data(as_text=True)
    assert 'name="sampling_id"' not in page and sampling.order.order_no not in page
    response = limited.post('/projects/create', data=dict(access_csrf='project-test',
        order_no='DENIED', description='Test', project_kind='sampling_work',
        reference_kind='sampling', sampling_id=sampling.id))
    assert response.status_code == 403 and Order.query.filter_by(order_no='DENIED').first() is None

    # Purpose changes preserve all history, and do not permit new irrelevant writes.
    repaired = Order.query.filter_by(order_no='P-TEST').one()
    before = (ToolPartEvent.query.count(), WorkTime.query.count(), Report.query.count(), Link.query.count())
    response = action(repaired, 'settings', project_kind='sampling_preparation',
        description='Jetzt Musterung vorbereiten', leader_id=admin.id)
    assert response.status_code == 303
    assert before == (ToolPartEvent.query.count(), WorkTime.query.count(), Report.query.count(), Link.query.count())
    page = c.get(f'/projects/{repaired.id}').get_data(as_text=True)
    assert 'Einbau / Ausbau dokumentieren' not in page and 'früherer Projekteinstufung' in page
    assert action(repaired, 'part').status_code == 422
    assert action(repaired, 'settings', project_kind='invalid', description='Fehler', leader_id=admin.id).status_code == 422
    assert db.session.get(Workspace, repaired.id).project_kind == 'sampling_preparation'
    assert Audit.query.filter_by(project_id=repaired.id, action='Projekteinstellungen').one().data['before']['project_kind'] == 'tool_repair'

    # An old project without a tool can be classified and assigned one together.
    old = Order.query.filter_by(order_no='OLD-PROJECT').one()
    assert action(old, 'settings', project_kind='tool_transfer', project_tool_id=tool.id,
        description='Werkzeug übernehmen', leader_id=admin.id).status_code == 303
    assert old.tool_no == tool.tool_no
    # Repeated installation must keep already selected purposes.
    run_upgrade(); run_upgrade()
    assert db.session.get(Workspace, old.id).project_kind == 'tool_transfer'

    # Simulate the exact previous workspace schema, then migrate twice.
    counts = (Order.query.count(), WorkTime.query.count(), Report.query.count(), ToolPartEvent.query.count())
    db.session.remove()
    db.session.execute(text('ALTER TABLE project_workspaces DROP COLUMN project_kind'))
    db.session.commit()
    run_upgrade(True)
    assert 'project_kind' not in {col['name'] for col in inspect(db.engine).get_columns('project_workspaces')}
    run_upgrade(); run_upgrade()
    assert counts == (Order.query.count(), WorkTime.query.count(), Report.query.count(), ToolPartEvent.query.count())
    assert all(w.project_kind == 'legacy' for w in Workspace.query.all())
    print('PASS: explicit purposes, required references, sampling-to-tool assignment, contextual sections, server-side gates, source permissions, preserved history and upgrade from previous schema twice')

# Verify backup-first upgrade on a real temporary SQLite file as well.
import tempfile, sqlite3
from flask import Flask
with tempfile.TemporaryDirectory(prefix='project_upgrade_', dir=Path(__file__).resolve().parents[2]) as folder:
    disk_app = Flask('project-upgrade-test')
    database = Path(folder) / 'test.db'
    disk_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(database)
    db.init_app(disk_app)
    with disk_app.app_context():
        db.create_all()
        db.session.add(Order(order_no='OLD-DISK', is_project=True, description='Vorhandenes Projekt', status='offen'))
        db.session.commit()
        db.session.execute(text("INSERT INTO project_workspaces (order_id, version) SELECT id, 7 FROM orders WHERE order_no='OLD-DISK'"))
        db.session.commit()
        db.session.execute(text('ALTER TABLE project_workspaces DROP COLUMN project_kind'))
        db.session.commit()
        run_upgrade(True); run_upgrade(backup=True); run_upgrade(backup=True)
        workspace = Workspace.query.one()
        assert workspace.project_kind == 'legacy' and workspace.version == 7
        backups = sorted((Path(folder) / 'backups').glob('*.db'))
        assert len(backups) == 2
        with sqlite3.connect(backups[0]) as saved:
            assert 'project_kind' not in {row[1] for row in saved.execute('PRAGMA table_info(project_workspaces)')}
            assert saved.execute('SELECT description FROM orders').fetchone()[0] == 'Vorhandenes Projekt'
        print('PASS: real SQLite migration preserves versions and creates a valid backup before altering the previous schema')
        db.session.remove(); db.engine.dispose()
