"""Local, position-aware proposals. No machine access; no cloud inference."""
import csv
import io
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
from factoryos.modules.masterdata.materials.services.material_scan_service import (
    engine_info, normalized_image, scan_slot, MAX_UPLOAD, ScanUnavailable)
from .schema import FIELDS

PAGES={"temperature":"TEMPERATUREN", "injection":"PROZESSOPTIMIERUNG", "movement":"WERKZEUG", "ejector":"AUSWERFER", "statistics":"PDE STATISTIK"}


def number(text):
    text=text.strip().replace(",",".")
    return text if re.fullmatch(r"-?\d+(?:\.\d+)?",text) else None


def blue_background(image,word):
    # Color is ONLY an additional exclusion signal, not the sole Soll/Ist rule.
    x,y,w,h=(word[k] for k in ("x","y","w","h"))
    samples=[image.getpixel((min(image.width-1,max(0,int(x+w*fx))),min(image.height-1,max(0,int(y+h*fy))))) for fx in (.1,.5,.9) for fy in (.1,.9)]
    return sum(b>r+18 and g>r+12 for r,g,b in samples)>=3


def parse_words(words, profile):
    groups=defaultdict(list)
    for word in words:groups[word.get("line",0)].append(word)
    lines=[sorted(line,key=lambda w:w["x"]) for line in groups.values()]
    text="\n".join(" ".join(w["text"] for w in line) for line in lines)
    upper=text.upper()
    page=next((key for key,title in PAGES.items() if title in upper),"unknown")
    result=dict(page=page,proposals=[],profiles={},text=text[:20000],notes=[])
    if profile!="nc5":
        result["notes"].append("Für diese Steuerung ist noch kein geprüftes Zuordnungsprofil vorhanden. Etiketttext als Hilfe verwenden und Werte manuell zuordnen.")
        return result
    if page=="unknown":
        result["notes"].append("NC5-Bildschirmseite nicht eindeutig erkannt. Keine automatische Zuordnung; bitte Ausschnitt oder Handeingabe verwenden.")
        return result
    if page=="statistics":
        result["notes"].append("PDE-Statistik enthält Messwerte, keine Sollparameter. Bewusst keine Übernahme als Soll-Zykluszeit oder Spritzdruck-Einstellung.")
        return result
    def add(key,word,label):
        val=number(word["text"])
        if val is not None and word.get("confidence",0)>=55:
            result["proposals"].append(dict(field=key,label=FIELDS[key]["label"],value=val,unit=FIELDS[key]["unit"],evidence=label+" / "+word["text"],status="open"))
    if page=="temperature":
        # Locate row labels and individual zone headers, never fixed image pixels.
        anchors={}
        for name,pattern in (("set",r"^soll$"),("actual",r"^ist$"),("plus",r"^tol\+?$"),("minus",r"^tol-?$")):
            found=[w for w in words if re.match(pattern,re.sub(r'[^a-z+\-]','',w["text"].lower()))]
            if name in ("set","actual") and len(found)>=1:anchors[name]=min(found,key=lambda w:w["y"])
        if "set" not in anchors or "actual" not in anchors:
            result["notes"].append("Soll-/Ist-Zeilen nicht sicher lokalisiert. Temperaturen bitte manuell prüfen.");return result
        if not 0<anchors['set']['y']-anchors['actual']['y']<max(anchors['set']['h'],anchors['actual']['h'])*5:
            result['notes'].append('Soll und Ist gehören nicht eindeutig zum selben Temperaturblock. Bitte manuell erfassen.');return result
        zones=[]
        for line in lines:
            for i,w in enumerate(line):
                token=w["text"].upper()
                if re.fullmatch(r"(?:DH|MH)\s*\d",token):zones.append((re.sub(r"([A-Z]+)(\d)",r"\1 \2",token),w))
                elif token in ("DH","MH") and i+1<len(line) and re.fullmatch(r"\d",line[i+1]["text"]):zones.append((token+" "+line[i+1]["text"],w))
                elif token=="EF":zones.append(("EF",w))
        zones=[(name,w) for name,w in zones if w["y"]<anchors["actual"]["y"]]
        if len(zones)<2 or len({name for name,_ in zones})!=len(zones):
            result["notes"].append("Zonenbeschriftung nicht eindeutig. Keine Temperaturzuordnung.");return result
        rows=[]
        zones.sort(key=lambda item:item[1]["x"])
        for name,zone in zones:
            values={}
            for kind,anchor in anchors.items():
                candidates=[w for w in words if number(w["text"]) is not None and w.get("confidence",0)>=55
                    and abs((w["y"]+w["h"]/2)-(anchor["y"]+anchor["h"]/2))<max(anchor["h"],w["h"])*.85
                    and abs((w["x"]+w["w"]/2)-(zone["x"]+zone["w"]/2))<max(zone["w"]*1.3,28)]
                if len(candidates)==1 and not (kind=="set" and candidates[0].get("blue")):
                    values[kind]=dict(value=number(candidates[0]["text"]),unit="°C")
            if values:rows.append(dict(label=name,active="unknown",values={key:values.get(key,dict(value="",unit="°C")) for key in ("set","actual","plus","minus")}))
        if rows:result["profiles"]["cylinder"]=dict(rows=rows,status="open",origin="photo",reason="")
        result["notes"].append("Nur lesbare Zonen wurden zugeordnet. Zonenliste kann unvollständig sein! Fehlende Zonen, Sollwerte, Toleranzen und Aktivierung am Foto ergänzen und einzeln bestätigen.")
    if page=="injection":
        # Grid uses the named row + named process column, not adjacent blue telemetry.
        def anchor(pattern):
            candidates=[w for w in words if re.fullmatch(pattern,w["text"],re.I)]
            return candidates[0] if len(candidates)==1 else None
        dose=anchor(r"Dosieren");delay=anchor(r"Verzögerung");cool=anchor(r"Kühlen");hold=anchor(r"ND");inject=anchor(r"Spritzen")
        row_anchors={}
        for name,pattern in (("speed",r"Geschwindigkeit"),("position",r"Position"),("pressure",r"Druck"),("time",r"Zeit")):
            row_anchors[name]=sorted([w for w in words if re.fullmatch(pattern,w["text"],re.I)],key=lambda w:w["y"])
        def cell(column,row_kind,half,field):
            if not column or len(row_anchors[row_kind])<2:return
            row=row_anchors[row_kind][half]
            candidates=[w for w in words if number(w["text"]) is not None and not w.get("blue")
                and w.get("confidence",0)>=55 and abs(w["y"]-row["y"])<max(w["h"],row["h"])*.8
                and abs((w["x"]+w["w"]/2)-(column["x"]+column["w"]/2))<max(column["w"]*.7,25)]
            if len(candidates)==1:add(field,candidates[0],column["text"]+" / "+row["text"])
        for column,kind,half,key in ((dose,"position",0,"dosing_position"),(dose,"pressure",0,"back_pressure"),
                (dose,"speed",0,"screw_speed"),(delay,"time",0,"dosing_delay"),(cool,"time",1,"cooling_time"),
                (inject,"pressure",1,"injection_pressure"),(hold,"speed",1,"holding_speed")):
            cell(column,kind,half,key)
        result["notes"].append("Nur eindeutig lokalisierte Einstellfelder werden vorgeschlagen. Mehrstufige Spritz-/Nachdruckprofile bitte über die jeweilige Profilseite ergänzen. Blaue Messwerte werden nicht als Einstellungen übernommen.")
    if page in ("movement","ejector"):
        result["notes"].append("Bewegungsseite erkannt. Stufenaktivierung, Vor-/Rücklauf und Werkzeugschutz müssen anhand des Fotos zugeordnet werden. Bitte Profilzeilen manuell erfassen; keine ungeprüfte Übernahme ausgegrauter Stufen.")
    return result


def screen_crop(image):
    """Conservative bright display detection; optional CV, no fixed photo coordinates."""
    try:
        import cv2
        import numpy as np
        if not hasattr(cv2,'findContours'):return image
        gray=cv2.cvtColor(np.array(image),cv2.COLOR_RGB2GRAY)
        mask=cv2.threshold(gray,135,255,cv2.THRESH_BINARY)[1]
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((25,25),np.uint8))
        contours=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]
        if not contours:return image
        largest=max(contours,key=cv2.contourArea)
        x,y,w,h=cv2.boundingRect(largest)
        if cv2.contourArea(largest)<image.width*image.height*.25 or not .9<w/h<2.3:return image
        box=(max(0,x-12),max(0,y-12),min(image.width,x+w+12),min(image.height,y+h+12))
        return image.crop(box)
    except (ImportError,AttributeError):return image


def read_screen(raw, profile):
    # Reuse the established image validation, engine resolution and cross-worker lock.
    checked=normalized_image(raw);checked.close()
    executable,languages=engine_info()
    with Image.open(io.BytesIO(raw)) as original:
        image=ImageOps.exif_transpose(original).convert("RGB");image.thumbnail((2400,2400));image.info.clear()
    cropped=screen_crop(image)
    if cropped is not image:image.close();image=cropped
    # Small HMI text needs enlargement; coordinates remain in the same RGB image.
    factor=min(2.5,3000/image.width,2400/image.height)
    if factor>1:image=image.resize((int(image.width*factor),int(image.height*factor)),Image.Resampling.LANCZOS)
    stream=io.BytesIO();image.save(stream,"JPEG",quality=85)
    if stream.tell()>3*1024*1024:raise ValueError("Aufbereitetes Foto ist zu groß. Bitte Bildschirm näher fotografieren.")
    with scan_slot(),tempfile.TemporaryDirectory(prefix="factoryos-setup-") as folder:
        source=Path(folder)/"screen.png"
        ImageOps.autocontrast(ImageOps.grayscale(image)).filter(ImageFilter.UnsharpMask(radius=1,percent=140,threshold=3)).save(source)
        output=Path(folder)/"screen.tsv"
        best=None
        for mode,timeout in ((11,10),(6,8)):
            try:
                with output.open("wb") as target:
                    subprocess.run([executable,str(source),"stdout","-l",languages,"--psm",str(mode),"tsv"],stdout=target,stderr=subprocess.DEVNULL,check=True,timeout=timeout,env=dict(os.environ,OMP_THREAD_LIMIT="1"))
            except subprocess.TimeoutExpired:
                if best:break
                raise ValueError("Foto-Erkennung hat zu lange gedauert. Entwurf bleibt erhalten; Handeingabe ist jederzeit möglich.")
            except (OSError,subprocess.CalledProcessError):
                if best:break
                raise ScanUnavailable("Lokale Bildschirm-Erkennung fehlgeschlagen. Handeingabe bleibt verfügbar.")
            if output.stat().st_size>2*1024*1024:raise ValueError("Zu viele Bildinformationen. Bitte nur den Bildschirm fotografieren.")
            words=[]
            for row in csv.DictReader(io.StringIO(output.read_text(errors="replace")),delimiter="\t",quoting=csv.QUOTE_NONE):
                if not row.get("text","").strip():continue
                try:
                    word=dict(text=row["text"],confidence=float(row["conf"]),x=int(row["left"]),y=int(row["top"]),w=int(row["width"]),h=int(row["height"]),line=tuple(row[k] for k in ("block_num","par_num","line_num")))
                    word["blue"]=blue_background(image,word);words.append(word)
                except (ValueError,KeyError):continue
                if len(words)>3000:raise ValueError("Zu viel Text. Bitte Bildausschnitt begrenzen.")
            if not words:continue
            current=parse_words(words,profile)
            rank=lambda r:(len(r['proposals'])+sum(len(p['rows']) for p in r['profiles'].values()),r['page']!='unknown',len(r['text']))
            if best is None or rank(current)>rank(best):best=current
    image.close()
    if not best:raise ValueError("Kein lesbarer Bildschirmtext. Bitte näher, gerade und ohne Spiegelungen fotografieren.")
    return stream.getvalue(),best
