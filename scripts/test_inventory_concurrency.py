"""Independent SQLite sessions compete for the same physical stock."""
import runpy,threading
from pathlib import Path
from uuid import uuid4
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_machine_control_concurrency.py'))
app=fixture['app'];uid=fixture['uid']
from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.inventory.models import WarehouseLot,WarehouseLocation,WarehouseReservation
from factoryos.modules.inventory.service import execute,revision,available
with app.app_context():
    article=Article(article_no='WH-RACE',article_name='Prüfteil');db.session.add(article);db.session.commit()
    def run(action,**data):return execute(uid,action,str(uuid4()),revision(),dict(confirmed='yes',reason='Konkurrenztest',**{k:str(v) for k,v in data.items()}))
    run('location',code='RACE',description='Testlager')
    place=WarehouseLocation.query.one();run('opening',article_id=article.id,batch='RACE',quantity=100,destination_id=place.id)
    lot=WarehouseLot.query.one();run('release',lot_id=lot.id,location_id=place.id,quantity=100)
    lid,pid,rev=lot.id,place.id,revision()
barrier=threading.Barrier(2);results=[];errors=[]
def worker():
    with app.app_context():
        barrier.wait(timeout=10)
        try:
            execute(uid,'reserve',str(uuid4()),rev,dict(confirmed='yes',reason='Konkurrenztest',lot_id=str(lid),location_id=str(pid),quantity='80',reference='LS-RACE'))
            results.append('ok')
        except ValueError:db.session.rollback();results.append('conflict')
        except Exception as error:db.session.rollback();errors.append(repr(error))
threads=[threading.Thread(target=worker) for _ in range(2)]
for t in threads:t.start()
for t in threads:t.join(timeout=25)
assert not any(t.is_alive() for t in threads) and not errors,errors
assert sorted(results)==['conflict','ok'],results
with app.app_context():assert WarehouseReservation.query.count()==1 and available(lid,pid)==20
print('PASS: competing reservations serialize across independent SQLite sessions; one succeeds, one conflicts; no over-reservation or deadlock.')
