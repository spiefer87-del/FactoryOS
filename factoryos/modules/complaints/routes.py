from flask import Blueprint,render_template
from flask_login import login_required
from factoryos.core.auth import permission_required
bp=Blueprint('complaints',__name__,url_prefix='/quality/complaints')
@bp.get('/')
@login_required
@permission_required('complaints.view')
def overview():return render_template('article_defects/complaints.html')
