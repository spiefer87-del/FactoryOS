"""Local OCR + conservative label proposals. Never creates/updates a material."""
import csv
import io
import os
import shutil
import subprocess
import tempfile
import warnings
from collections import OrderedDict
from pathlib import Path
from contextlib import contextmanager
from flask import current_app,has_app_context
from PIL import Image,ImageOps,ImageFilter,UnidentifiedImageError
from .material_label_rules import parse_label,MAX_TEXT

MAX_UPLOAD=10*1024*1024
MAX_PIXELS=24_000_000

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

def _recognition_rank(result):
    """Prefer usable labelled fields over a long list of barcode fragments."""
    text,confidence=result
    if sum(c.isalnum() for c in text)<5:return (-1,0,0)
    fields=parse_label(text)["proposals"]
    score=sum(3 if field["field"] in ("name","manufacturer") else 1 for field in fields)
    # OCR spelling corrections are suggestions, not evidence of a better pass.
    score-=sum(2 for field in fields if "normalisiert" in field.get("note",""))
    score-=sum(2 for field in fields if "Nur Grade" in field.get("note",""))
    return score,confidence or 0,min(len(text),MAX_TEXT)

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
                except subprocess.TimeoutExpired:
                    if _recognition_rank(best)[0]>=0:break
                    raise ValueError("Texterkennung hat zu lange gedauert. Bitte nur das Etikett scharf und gerade fotografieren.")
                except (OSError,subprocess.CalledProcessError):
                    if _recognition_rank(best)[0]>=0:break
                    raise ScanUnavailable("Texterkennung fehlgeschlagen. Bitte Foto oder lokale OCR-Installation prüfen.")
                if output.stat().st_size>2*1024*1024:
                    if _recognition_rank(best)[0]>=0:break
                    raise ValueError("Zu viel Text erkannt. Bitte den Ausschnitt auf das Materialetikett begrenzen.")
                current=_tsv(output.read_text(encoding="utf-8",errors="replace"))
                if _recognition_rank(current)>_recognition_rank(best):best=current
                # Try both sparse and block layouts; do not mix conflicting readings.
    if sum(c.isalnum() for c in best[0])<5:raise ValueError("Kein lesbarer Text gefunden. Etikett näher, scharf und ohne Spiegelung fotografieren.")
    return best[0],best[1],languages
