"""Label spelling/layout rules, not a chemistry/product-knowledge database."""
import re
from difflib import SequenceMatcher
from factoryos.modules.masterdata.shared.constants import POLYMER_TYPES

MAX_TEXT=20000
FIELDS={"manufacturer":"Hersteller","name":"Genaue Bezeichnung / Handelsname",
    "external_material_no":"Externe Materialnummer","material_type":"Materialart",
    "polymer_type":"Kunststoffart","color":"Farbe","color_no":"Farbnummer",
    "ral_color":"Farbton / RAL","delivery_form":"Lieferform"}
MAKERS=("ENVALIOR","BASF","SABIC","COVESTRO","INEOS","LYONDELLBASELL","CELANESE","LANXESS","DOMO","RAVAGO")
# Literal text spellings only; NO family -> manufacturer or polymer mapping.
FAMILIES=("DURETHAN","ULTRAMID","ULTRADUR","TERLURAN","LUSTRAN","CYCOLAC","MAKROLON","LEXAN","HOSTAFORM","ZYTEL","TECHNYL","AKULON","ARNITE")
NON_PRODUCT=re.compile(r"(?:\b(?:partie|party|parle|perle|parie|batch|charge|chargen|lot|los|weight|gewicht|netto|gross|date|datum|order|auftrag|barcode|ean|iso|phone|tel|www|colou?r|farbe|farbnummer|ral)\b|^(?:partie|perle|parle)(?=\d)|\b\d+(?:[.,]\d+)?\s*(?:kg|lb|lbs)\b|\bUN\s*\d)",re.I)
GRADE=r"typ\s*/\s*type|type\s*/\s*typ|grade|type|typ|sorte"
COLOR=r"farbe\s*/?\s*colou?r|colou?r\s*/\s*farbe|colou?r(?: name)?|farbe|farbton"
MAKER=r"hersteller\s*/\s*manufacturer|manufacturer\s*/\s*hersteller|manufacturer|hersteller|produced by|manufactured by|producer"
PRODUCT=r"produkt\s*/\s*product|product(?: name)?|produkt(?:name|bezeichnung)?|handelsname|trade name|bezeichnung|material(?: name|bezeichnung)"
BATCH=r"partie\s*/\s*lot|charge\s*/\s*batch|batch\s*/\s*charge|lot(?:\s*(?:no\.?|number))?|partie|party|charge(?:n[- ]?nr\.?)?|batch(?:\s*(?:no\.?|number))?|los(?:nummer)?|perle|parle|parie"

def compact(value):return re.sub(r"[^A-Z]","",value.upper())

def printed_header(lines):
    """Match printed company tokens; uncertain OCR corrections always need review."""
    found=[]
    for line in lines[:12]:
        if NON_PRODUCT.search(line) or re.search(r"https?://|@",line,re.I):continue
        matched=None;end=None;corrected=False
        for maker in MAKERS:
            match=re.match(r"^[^A-Za-z0-9]*"+r"\s*".join(maker)+r"(?![A-Za-z])",line,re.I)
            if match:matched=maker;end=match.end();break
        if not matched:
            first=re.match(r"^[^A-Za-z0-9]*([A-Za-z0-9]{5,16})(?=\s|[-–—]|$)",line)
            if first:
                token=first[1].upper().replace("0","O")
                ranked=sorted(((SequenceMatcher(None,token,m).ratio(),m) for m in MAKERS if len(m)>=6 and abs(len(token)-len(m))<=3),reverse=True)
                if ranked and ranked[0][0]>=.70 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.12):
                    matched=ranked[0][1];end=first.end();corrected=True
        if matched:found.append(dict(maker=matched,line=line,suffix=line[end:].strip(" -–—|:®™"),corrected=corrected))
    distinct={f["maker"] for f in found}
    return (found[0] if len(distinct)==1 else None),len(distinct)>1

def family_spelling(value):
    value=value.strip(" -–—|:®™")
    clean=compact(value)
    if not clean or len(value)>65 or re.search(r"\d|[:=@/]|\b(?:gmbh|street|strasse|straße|road|tel|fax|se|ag)\b",value,re.I):return None,False
    for family in FAMILIES:
        if clean==family:return family,False
    ranked=sorted(((SequenceMatcher(None,clean,f).ratio(),f) for f in FAMILIES if len(f)>=7 and abs(len(clean)-len(f))<=2),reverse=True)
    if ranked and ranked[0][0]>=.84 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.12):return ranked[0][1],True
    return None,False

def parse_label(text):
    if not isinstance(text,str) or len(text)>MAX_TEXT:raise ValueError("Etiketttext darf höchstens 20.000 Zeichen enthalten.")
    lines=[re.sub(r"[ \t]+"," ",line).strip() for line in text.replace("\x00","").splitlines() if line.strip()]
    if not lines:raise ValueError("Bitte erst ein Foto auslesen oder Etiketttext eingeben.")
    proposals={};notes=[];metadata=[]
    def add(field,value,evidence,certainty="label",note=""):
        if not value:return
        limit=200 if field=="name" else 150 if field=="manufacturer" else 100
        proposals[field]=dict(field=field,label=FIELDS[field],value=value.strip()[:limit],evidence=evidence[:400],certainty=certainty,note=note)
    any_label=re.compile(r"^(?:"+"|".join((GRADE,COLOR,MAKER,PRODUCT,BATCH,r"material no\.?|netto|net weight|delivery form|lieferform"))+r")\s*[:=]?\s*$",re.I)
    def labelled(pattern,guard=False):
        direct=re.compile(r"^(?:"+pattern+r")\s*(?::|=|\s[-–]\s)\s*(.+)$",re.I)
        alone=re.compile(r"^(?:"+pattern+r")\s*[:=]?\s*$",re.I)
        spaced=re.compile(r"^(?:"+pattern+r")\s+(.+)$",re.I)
        for index,line in enumerate(lines):
            if alone.match(line):
                for following in lines[index+1:index+4]:
                    if re.fullmatch(r"[|_\-–—. ]+",following):continue
                    if any_label.match(following) or re.search(r"[:=]",following) or NON_PRODUCT.search(following):break
                    return following,line+" / "+following
                continue
            match=direct.match(line) or spaced.match(line)
            if match:
                value=match[1].strip()
                if value.startswith("/") or re.match(r"(?:code|id|number|no\.?|nummer|nr\.?)\b",value,re.I):continue
                if guard and NON_PRODUCT.search(value):continue
                return value,line
        return None,None

    header,ambiguous_makers=printed_header(lines)
    manufacturer,evidence=labelled(MAKER)
    if manufacturer:add("manufacturer",manufacturer,evidence)
    elif header:add("manufacturer",header["maker"],header["line"],"review",
        "OCR-Schreibweise des Herstellernamens normalisiert – am Foto bestätigen." if header["corrected"] else "Name aus dem Etikettkopf – Hersteller/Lieferant am Foto bestätigen.")
    elif ambiguous_makers:notes.append("Mehrere Herstellernamen im Aufdruck – Hersteller bitte bewusst auswählen.")
    product,product_line=labelled(PRODUCT,True)
    grade,grade_line=labelled(GRADE,True)
    if grade:metadata.append(dict(label="Typ / Grade",value=grade,evidence=grade_line))
    corrected_family=False
    if not product:
        family=None;family_line=None
        if header and header["suffix"]:
            family,corrected_family=family_spelling(header["suffix"])
            if not family and re.search(r"[-–—]",header["line"]) and not NON_PRODUCT.search(header["suffix"]) and re.fullmatch(r"[A-Za-z®™][A-Za-z®™ ]{3,40}",header["suffix"]):
                family=header["suffix"]
            if family:family_line=header["line"]
        if not family:
            family_candidates=[]
            for line in lines[:12]:
                if NON_PRODUCT.search(line):continue
                value,changed=family_spelling(line)
                if value:family_candidates.append((value,line,changed))
            if len({value for value,_,_ in family_candidates})==1:
                family,family_line,corrected_family=family_candidates[0]
        if family:product,product_line=family,family_line
    if product:
        value=product if not grade or grade.lower() in product.lower() else product+" "+grade
        note="Handelsname und Typ/Grade aus getrennten Etikettzeilen – vollständig prüfen."
        if corrected_family:note+=" OCR-Schreibweise des Handelsnamens normalisiert."
        certainty="label" if product_line and re.match(r"^(?:"+PRODUCT+r")[ :=]",product_line,re.I) and not grade else "review"
        add("name",value,product_line+(" / "+grade_line if grade_line else ""),certainty,note if certainty=="review" else "")
    elif grade:add("name",grade,grade_line,"review","Nur Grade/Typ gefunden – vollständigen Handelsnamen prüfen.")
    else:
        candidates=[line for line in lines if len(line)<=100 and re.search(r"[A-Za-z]{3}",line) and re.search(r"\d",line)
            and not NON_PRODUCT.search(line) and not re.search(r"[:=]",line)]
        if len(candidates)==1:add("name",candidates[0],candidates[0],"review","Unbeschriftete Produktzeile vermutet – Handelsname/Grade prüfen.")
        elif candidates:notes.append("Mehrere mögliche Produktzeilen. Bezeichnung bitte anhand des Fotos ergänzen.")
    value,evidence=labelled(r"material(?: number| no\.?| code|nummer)|product(?: code| id| number| no\.?)|artikel(?:nummer|[- ]?nr\.?)|article(?: no\.?| number)|item code")
    if value:add("external_material_no",value,evidence,"review","Externe Produktnummer, nicht interne Materialnummer. Charge/Los nicht übernehmen.")

    categories=[]
    for key,pattern in (("masterbatch",r"\b(?:master\s*batch|farb\s*batch|color\s*batch|colour\s*batch)\b"),("operating",r"\bBetriebsstoff\b"),("auxiliary",r"\bHilfsstoff\b")):
        found=next((line for line in lines if re.search(pattern,line,re.I)),None)
        if found:categories.append((key,found))
    if len(categories)==1:add("material_type",categories[0][0],categories[0][1])
    elif len(categories)>1:notes.append("Mehrere Materialkategorien erkannt. Einordnung bitte selbst festlegen.")
    aliases={"PC_ABS":r"PC\s*[/+\-]\s*ABS","PE_HD":r"(?:PE[ -]?HD|HDPE)","PE_LD":r"(?:PE[ -]?LD|LDPE)",
        "PA66":r"PA\s*6[.,]?6","PA6":r"PA\s*6(?![.,]6)","PA11":r"PA\s*11","PA12":r"PA\s*12"}
    polymers=[]
    for key in POLYMER_TYPES:
        if key=="OTHER":continue
        found=next((line for line in lines if re.search(r"(?<![A-Za-z0-9])(?:"+aliases.get(key,re.escape(key))+r")(?![A-Za-z0-9])",line,re.I)),None)
        if found:polymers.append((key,found))
    if any(k=="PC_ABS" for k,_ in polymers):polymers=[p for p in polymers if p[0] not in ("PC","ABS")]
    if len(polymers)==1 and not categories:add("polymer_type",*polymers[0]);add("material_type","plastic",polymers[0][1])
    elif len(polymers)>1:notes.append("Mehrere Kunststoffarten gefunden. Keine automatische Kunststoffzuordnung.")
    elif not polymers and not categories:notes.append("Kunststoffart ist nicht als eindeutiges Kürzel auf dem Etikett lesbar. Keine Ableitung aus Handelsnamen – bitte Datenblatt/Stammdaten prüfen.")

    value,evidence=labelled(COLOR)
    if value:
        if re.search(r"\bRAL\s*\d{4}\b",value,re.I):pass
        elif re.fullmatch(r"(?=.*\d)[A-Za-z0-9][A-Za-z0-9._/\-]{0,39}",value):
            add("color_no",value,evidence,"review","Farbcode aufgedruckt; daraus wird keine Farbbezeichnung oder RAL geraten.")
        else:add("color",value,evidence)
    value,evidence=labelled(r"colou?r(?: no\.?| number| code)|farb(?:nummer|[- ]?nr\.?)")
    if value:add("color_no",value,evidence)
    ral=next((re.search(r"\bRAL\s*[-:]?\s*(\d{4})\b",line,re.I) for line in lines if re.search(r"\bRAL\s*[-:]?\s*\d{4}\b",line,re.I)),None)
    if ral:add("ral_color","RAL "+ral[1],ral[0])
    value,evidence=labelled(r"delivery form|lieferform|form")
    if value:
        for key,pattern in (("granulate",r"granulat|pellet"),("powder",r"pulver|powder"),("liquid",r"flüssig|liquid"),("paste",r"paste"),("solid",r"feststoff|solid"),("film",r"folie|film")):
            if re.search(pattern,value,re.I):add("delivery_form",key,evidence);break
    lot,lot_line=labelled(BATCH)
    if lot and re.search(r"\d",lot):metadata.append(dict(label="Partie / Los (kein Materialname)",value=lot[:100],evidence=lot_line))
    for line in lines:
        weight=re.search(r"(?:net\s*weight|netto(?:gewicht)?|gewicht|weight)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(kg|g|lbs?)\b",line,re.I)
        if weight:metadata.append(dict(label="Sack-/Gewichtsangabe (kein Bestand)",value=weight[1]+" "+weight[2],evidence=line));break
    notes.extend(("OCR ist eine Ausfüllhilfe: jede Angabe am Etikett prüfen. Lesbarkeit ist keine fachliche Gewissheit.",
        "Interne Materialnummer, Gefahrstoffstatus, Verarbeitungsvorgaben, Bestände und Lieferantenverknüpfung werden nicht automatisch gesetzt. Sackgewicht, Charge und Los sind keine Materialidentität."))
    missing=[dict(field=field,label=label,reason="Nicht eindeutig auf dem Etikett erkannt – bitte manuell ergänzen.") for field,label in FIELDS.items() if field not in proposals]
    return dict(text="\n".join(lines),proposals=[proposals[k] for k in FIELDS if k in proposals],notes=notes,missing_fields=missing,label_metadata=metadata)
