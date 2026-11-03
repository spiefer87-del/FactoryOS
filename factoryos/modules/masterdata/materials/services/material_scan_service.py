"""Local OCR + conservative label proposals. Never creates/updates a material."""
import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
import warnings
from collections import OrderedDict
from pathlib import Path
from contextlib import contextmanager
from flask import current_app,has_app_context
from PIL import Image,ImageOps,ImageFilter,UnidentifiedImageError
from factoryos.modules.masterdata.shared.constants import POLYMER_TYPES

MAX_UPLOAD=10*1024*1024
MAX_PIXELS=24_000_000
MAX_TEXT=20000
FIELDS={"name":"Genaue Bezeichnung / Handelsname","manufacturer":"Hersteller",
    "external_material_no":"Externe Materialnummer","material_type":"Materialart",
    "polymer_type":"Kunststoffart","color":"Farbe","color_no":"Farbnummer",
    "ral_color":"Farbton / RAL","delivery_form":"Lieferform"}

class ScanUnavailable(ValueError):pass
class ScanBusy(ValueError):pass

def resolve_tesseract():
    """Do not depend on systemd's often venv-only PATH. No shell invocation."""
    configured=(current_app.config.get("TESSERACT_CMD") if has_app_context() else None) or os.environ.get("FACTORYOS_TESSERACT_CMD")
    if configured:
        path=Path(configured)
        if not path.is_absolute() or not path.is_file() or not os.access(path,os.X_OK):
            raise ScanUnavailable("Der konfigurierte Tesseract-Pfad ist nicht ausführbar. FACTORYOS_TESSERACT_CMD bzw. TESSERACT_CMD prüfen.")
        return str(path)
    for candidate in (shutil.which("tesseract"),"/usr/bin/tesseract","/usr/local/bin/tesseract","/bin/tesseract"):
        if candidate and Path(candidate).is_file() and os.access(candidate,os.X_OK):return str(candidate)
    raise ScanUnavailable("Tesseract ist für den FactoryOS-Dienst weder im Suchpfad noch in den Systempfaden auffindbar. scripts/check_material_scan.py ausführen und Ausgabe weitergeben.")

def engine_info():
    executable=resolve_tesseract()
    try:
        result=subprocess.run([executable,"--list-langs"],capture_output=True,text=True,timeout=3,check=True)
    except (OSError,subprocess.SubprocessError):raise ScanUnavailable("Lokale Texterkennung ist nicht verfügbar. Installation prüfen.")
    languages=set(result.stdout.splitlines())
    selected=[lang for lang in ("deu","eng") if lang in languages]
    if not selected:raise ScanUnavailable("OCR-Sprachpakete fehlen. tesseract-ocr-deu und tesseract-ocr-eng installieren.")
    return executable,"+".join(selected)

@contextmanager
def scan_slot():
    import fcntl
    # Cross-worker lock. Only an empty lock file persists, never photo/text.
    folder=Path(current_app.instance_path);folder.mkdir(parents=True,exist_ok=True)
    with (folder/"material_scan.lock").open("a") as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ScanBusy("Eine Texterkennung läuft bereits. Bitte kurz warten und erneut versuchen.")
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)

def normalized_image(data):
    if not data:raise ValueError("Bitte ein Foto auswählen.")
    if len(data)>MAX_UPLOAD:raise ValueError("Foto ist größer als 10 MB. Bitte Kameraauflösung reduzieren oder das Etikett näher fotografieren.")
    if not (data.startswith(b"\xff\xd8") or data.startswith(b"\x89PNG\r\n\x1a\n") or (data.startswith(b"RIFF") and data[8:12]==b"WEBP")):
        raise ValueError("Bitte ein JPEG-, PNG- oder WebP-Foto verwenden (kein HEIC/PDF/SVG).")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ("JPEG","PNG","WEBP"):raise ValueError("Bitte ein JPEG-, PNG- oder WebP-Foto verwenden (kein HEIC/PDF/SVG).")
                width,height=image.size
                if min(width,height)<100 or max(width,height)>10000 or width*height>MAX_PIXELS:
                    raise ValueError("Foto muss mindestens 100 × 100 Pixel und höchstens 24 Megapixel haben.")
                if getattr(image,"n_frames",1)!=1:raise ValueError("Bitte ein einzelnes Standbild verwenden.")
                image.load()
                copy=ImageOps.exif_transpose(image).convert("RGB")
                copy.thumbnail((2400,2400))
                copy=ImageOps.autocontrast(ImageOps.grayscale(copy)).filter(ImageFilter.UnsharpMask(radius=1,percent=120,threshold=3))
                copy=ImageOps.expand(copy,border=24,fill=255)
                copy.info.clear()
                return copy
    except (UnidentifiedImageError,OSError,SyntaxError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValueError("Foto kann nicht sicher gelesen werden. Bitte ein neues JPEG-/PNG-/WebP-Foto aufnehmen.")

def _tsv(data):
    lines=OrderedDict();conf=[]
    for row in csv.DictReader(io.StringIO(data),delimiter="\t"):
        text=(row.get("text") or "").strip()
        if not text:continue
        try:score=float(row.get("conf","-1"))
        except ValueError:score=-1
        if score>=0:conf.append(max(0,min(100,score)))
        key=tuple(row.get(k,"") for k in ("page_num","block_num","par_num","line_num"))
        lines.setdefault(key,[]).append(text)
    text="\n".join(" ".join(words) for words in lines.values())
    return text[:MAX_TEXT],round(sum(conf)/len(conf)) if conf else None

def read_label(data):
    executable,languages=engine_info()
    with scan_slot():
        image=normalized_image(data)
        with tempfile.TemporaryDirectory(prefix="factoryos-label-",dir=current_app.config.get("MATERIAL_SCAN_TMP_DIR")) as directory:
            source=Path(directory)/"label.png"
            try:image.save(source,"PNG")
            finally:image.close()
            best=("",None)
            for mode,timeout in ((11,10),(6,8)):
                output=Path(directory)/"output.tsv";errors=Path(directory)/"errors.txt"
                env=dict(os.environ,OMP_THREAD_LIMIT="1")
                try:
                    with output.open("wb") as stream,errors.open("wb") as stderr:
                        subprocess.run([executable,str(source),"stdout","-l",languages,"--psm",str(mode),"tsv"],
                            stdout=stream,stderr=stderr,timeout=timeout,check=True,env=env)
                except subprocess.TimeoutExpired:raise ValueError("Texterkennung hat zu lange gedauert. Bitte nur das Etikett scharf und gerade fotografieren.")
                except (OSError,subprocess.CalledProcessError):raise ScanUnavailable("Texterkennung fehlgeschlagen. Bitte Foto oder lokale OCR-Installation prüfen.")
                if output.stat().st_size>2*1024*1024:raise ValueError("Zu viel Text erkannt. Bitte den Ausschnitt auf das Materialetikett begrenzen.")
                current=_tsv(output.read_text(encoding="utf-8",errors="replace"))
                if len(current[0])>len(best[0]):best=current
                if sum(c.isalnum() for c in best[0])>=20:break
    if sum(c.isalnum() for c in best[0])<5:raise ValueError("Kein lesbarer Text gefunden. Etikett näher, scharf und ohne Spiegelung fotografieren.")
    return best[0],best[1],languages

def parse_label(text):
    if not isinstance(text,str) or len(text)>MAX_TEXT:raise ValueError("Etiketttext darf höchstens 20.000 Zeichen enthalten.")
    text=text.replace("\x00","")
    lines=[re.sub(r"[ \t]+"," ",line).strip() for line in text.splitlines() if line.strip()]
    if not lines:raise ValueError("Bitte erst ein Foto auslesen oder Etiketttext eingeben.")
    proposals={};notes=[]
    def add(field,value,evidence,certainty="label",note=""):
        if field not in FIELDS or not value:return
        limit=200 if field=="name" else 150 if field=="manufacturer" else 100
        value=value.strip()[:limit]
        proposals[field]=dict(field=field,label=FIELDS[field],value=value,evidence=evidence[:400],certainty=certainty,note=note)
    def labelled(pattern):
        regex=re.compile(r"^\s*(?:"+pattern+r")\s*(?::|=|\s[-–]\s)\s*(.+)$",re.I)
        alone=re.compile(r"^(?:"+pattern+r")\s*[:=]?\s*$",re.I)
        spaced=re.compile(r"^(?:"+pattern+r")\s+(.+)$",re.I)
        for index,line in enumerate(lines):
            match=regex.match(line)
            if match and match[1].strip():return match[1].strip(),line
            if alone.match(line) and index+1<len(lines):
                value=lines[index+1]
                next_label=re.fullmatch(r"(?:product(?: name)?|produkt(?:name|bezeichnung)?|grade|type|typ|manufacturer|hersteller|colou?r|farbe|farbnummer|lieferform)",value,re.I)
                if not next_label and not re.search(r"[:=]",value) and not re.match(r"(?:batch|lot|charge|net|gross|weight|gewicht|date|datum)\b",value,re.I):
                    return value,line+" / "+value
            match=spaced.match(line)
            if match and not re.match(r"(?:code|id|number|no\.?|nummer|nr\.?)\b",match[1],re.I):return match[1].strip(),line
        return None,None
    product,product_line=labelled(r"product(?: name)?|produkt(?:name|bezeichnung)?|handelsname|trade name|bezeichnung|material(?: name|bezeichnung)")
    grade,grade_line=labelled(r"grade|type|typ|sorte")
    if product:
        if grade and grade.lower() not in product.lower():
            add("name",product+" "+grade,product_line+" / "+grade_line,"review","Aus Produkt- und Gradezeile zusammengesetzt – Bezeichnung prüfen.")
        else:add("name",product,product_line)
    elif grade:add("name",grade,grade_line,"review","Nur Grade/Typ gefunden – vollständigen Handelsnamen prüfen.")
    else:
        candidates=[line for line in lines if len(line)<=100 and re.search(r"[A-Za-z]{3}",line) and re.search(r"\d",line)
            and not re.search(r"(?:batch|charge|lot|los|weight|gewicht|net|gross|date|datum|order|auftrag|kg|g/|iso|phone|tel|www|colou?r|farb|\bRAL\b|\bzip\b|\bUN\s*\d)",line,re.I)
            and not re.search(r"[:=]",line)]
        if len(candidates)==1:add("name",candidates[0],candidates[0],"review","Unbeschriftete Produktzeile vermutet – Handelsname/Grade unbedingt prüfen.")
        elif candidates:notes.append("Mehrere mögliche Produktzeilen. Bezeichnung bitte anhand des Fotos ergänzen.")
    manufacturer,evidence=labelled(r"manufacturer|hersteller|produced by|manufactured by|producer")
    if manufacturer:add("manufacturer",manufacturer,evidence)
    else:
        # Literal printed names only. Not product knowledge or proof of manufacturer.
        found=[line for line in lines if re.fullmatch(r"(?:BASF|SABIC|Covestro|INEOS|LyondellBasell|Celanese|LANXESS|DOMO|Envalior)(?: SE| AG| GmbH)?",line,re.I)]
        if len(found)==1:add("manufacturer",found[0],found[0],"review","Name auf dem Sack gefunden – Hersteller/Lieferant bitte unterscheiden.")
    value,evidence=labelled(r"material(?: number| no\.?| code|nummer)|product(?: code| id| number| no\.?)|artikel(?:nummer|[- ]?nr\.?)|article(?: no\.?| number)|item code")
    if value:add("external_material_no",value,evidence,"review","Externe Produktnummer, nicht interne Materialnummer. Chargen-/Losnummer nicht übernehmen.")
    categories=[]
    for key,pattern in (("masterbatch",r"\b(?:master\s*batch|farb\s*batch|color\s*batch|colour\s*batch)\b"),("operating",r"\bBetriebsstoff\b"),("auxiliary",r"\bHilfsstoff\b")):
        found=next((line for line in lines if re.search(pattern,line,re.I)),None)
        if found:categories.append((key,found))
    if len(categories)==1:add("material_type",categories[0][0],categories[0][1])
    elif len(categories)>1:notes.append("Mehrere Materialkategorien erkannt. Einordnung bitte selbst festlegen.")
    aliases={"PC_ABS":r"PC\s*[/+\-]\s*ABS", "PE_HD":r"(?:PE[ -]?HD|HDPE)","PE_LD":r"(?:PE[ -]?LD|LDPE)",
        "PA66":r"PA\s*6[.,]?6","PA6":r"PA\s*6(?![.,]6)","PA11":r"PA\s*11","PA12":r"PA\s*12"}
    polymers=[]
    for key in POLYMER_TYPES:
        if key=="OTHER":continue
        pattern=aliases.get(key,re.escape(key))
        found=next((line for line in lines if re.search(r"(?<![A-Za-z0-9])(?:"+pattern+r")(?![A-Za-z0-9])",line,re.I)),None)
        if found:polymers.append((key,found))
    if any(key=="PC_ABS" for key,_ in polymers):polymers=[p for p in polymers if p[0] not in ("PC","ABS")]
    if len(polymers)==1 and not categories:
        add("polymer_type",*polymers[0]);add("material_type","plastic",polymers[0][1])
    elif len(polymers)>1:notes.append("Mehrere Kunststoffarten gefunden. Keine automatische Kunststoffzuordnung.")
    elif not polymers and not categories:notes.append("Materialart/Kunststoffart nicht eindeutig erkannt – bitte selbst auswählen.")
    value,evidence=labelled(r"colou?r(?: name)?|farbe|farbton")
    if value:add("color",value,evidence)
    value,evidence=labelled(r"colou?r(?: no\.?| number| code)|farb(?:nummer|[- ]?nr\.?)")
    if value:add("color_no",value,evidence)
    ral=next((re.search(r"\bRAL\s*[-:]?\s*(\d{4})\b",line,re.I) for line in lines if re.search(r"\bRAL\s*[-:]?\s*\d{4}\b",line,re.I)),None)
    if ral:add("ral_color","RAL "+ral[1],ral[0])
    value,evidence=labelled(r"delivery form|lieferform|form")
    if value:
        for key,pattern in (("granulate",r"granulat|pellet"),("powder",r"pulver|powder"),("liquid",r"flüssig|liquid"),("paste",r"paste"),("solid",r"feststoff|solid"),("film",r"folie|film")):
            if re.search(pattern,value,re.I):add("delivery_form",key,evidence);break
    notes.append("OCR ist eine Ausfüllhilfe: jede Angabe am Etikett prüfen. Lesbarkeit ist keine fachliche Gewissheit.")
    notes.append("Interne Materialnummer, Gefahrstoffstatus, Verarbeitungsvorgaben, Bestände und Lieferantenverknüpfung werden nicht automatisch gesetzt. Sackgewicht, Charge und Los sind keine Materialidentität.")
    return dict(text="\n".join(lines),proposals=list(proposals.values()),notes=notes)
