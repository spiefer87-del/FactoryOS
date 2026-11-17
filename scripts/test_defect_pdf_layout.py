"""PDF display-only regression. No database or existing user photo touched."""
from pathlib import Path
from types import SimpleNamespace as Row
from datetime import datetime
import importlib.util,subprocess
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('catalog_pdf',root/'factoryos/modules/article_defects/pdf_export.py');pdf=importlib.util.module_from_spec(spec);spec.loader.exec_module(pdf)
folder=root/'tmp/pdfs/layout_update';folder.mkdir(parents=True,exist_ok=True)
photo=Image.new('RGB',(1000,700),'#edf2f7');draw=ImageDraw.Draw(photo);draw.rounded_rectangle((150,120,850,580),80,fill='#154f69');draw.ellipse((320,220,600,460),fill='#5394a8');photo.save(folder/'example.jpg','JPEG')
entry=Row(id=1,title='Nicht richtig durchgefärbt',defect_type='Farbabweichungen / Farbschlieren',description='Farbabweichung durch farbiges Mahlgut.',remedy='Masterbatch-Anteil prüfen / anderen Rohstoff verwenden.',article=Row(article_no='101010005',article_name='Winkel-Endkappe XL-14 mit Logo'),tool_no='ATH004',archived=True,version=6,created_at=datetime(2026,11,17,9,26),updated_at=datetime(2026,11,17,12,43),author=Row(username='admin'),photos=[Row(filename='example.jpg')])
before=vars(entry).copy()
output=folder/'layout.pdf';output.write_bytes(pdf.build_pdf([entry],folder).getvalue())
text=subprocess.check_output(['pdftotext',str(output),'-']).decode()
assert text.index('Farbabweichung')<text.index('Beobachteter Fehler')<text.index('Nicht richtig durchgefärbt')<text.index('Farbabweichung durch farbiges Mahlgut.')
assert 'FactoryOS' not in text and 'Qualität | Fehlerkatalog' not in text
assert vars(entry)==before and 'Masterbatch-Anteil' in text and 'Foto 1' in text
entry.defect_type='Grat / Schwimmhaut';entry.description=('Lange Beschreibung mit Umlauten äöü und <Sonderzeichen>.\n'*100)
(folder/'long.pdf').write_bytes(pdf.build_pdf([entry],folder).getvalue())
assert pdf.category_heading(entry.defect_type)=='Grat / Schwimmhaut'
print('PASS: no branding band/text; category at top; original short title under observed error; detailed description retained; no data mutation; long document and other categories')
