"""Master-derived names/tools for manual orders; no bulk changes to old orders."""
import re
from sqlalchemy.orm import selectinload
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from .cycle_time import parse_cycle_time,valid_cycle_time

MAX_QTY=2147483647
STATUS_LABELS={"open":"Offen","offen":"Offen","in_arbeit":"In Arbeit","running":"In Arbeit",
    "fertig":"Fertig","finished":"Fertig","gesperrt":"Gesperrt","locked":"Gesperrt",
    "cancelled":"Storniert","canceled":"Storniert","storniert":"Storniert","abgeschlossen":"Fertig"}

def status_label(value):
    return STATUS_LABELS.get((value or "").lower(),(value or "Nicht angegeben").replace("_"," "))

def parse_quantity(value):
    raw=str(value or "").strip()
    if not re.fullmatch(r"[0-9]{1,10}",raw) or not 1<=int(raw)<=MAX_QTY:
        raise ValueError("Eine Stückzahl ist Pflicht: bitte eine ganze Zahl von 1 bis 2.147.483.647 angeben.")
    return int(raw)

def _text(form,key,limit,required=False):
    value=(form.get(key) or "").strip()
    if (required and not value) or len(value)>limit:
        raise ValueError(f"{dict(order_no='Auftragsnummer',description='Beschreibung',location='Standort').get(key,key)}: {'Angabe erforderlich; ' if required else ''}höchstens {limit} Zeichen.")
    return value or None

def validate_form(form,order=None):
    project=bool(order and order.is_project)
    data=dict(description=_text(form,"description",255),location=_text(form,"location",100))
    if order:
        status=form.get("status",order.status)
        if status not in STATUS_LABELS and status!=order.status:raise ValueError("Ungültiger Auftragsstatus.")
        data["status"]=status
    else:data["order_no"]=_text(form,"order_no",50,True)
    if project:
        # Projects keep their existing, non-piece-based data and separate workflow.
        return data
    article_no=(form.get("article") or "").strip()
    article=Article.query.options(selectinload(Article.tools)).filter_by(article_no=article_no).first()
    if not article:raise ValueError("Bitte eine vorhandene Artikelnummer aus den Stammdaten auswählen.")
    if not (article.article_name or "").strip():raise ValueError("Im Artikelstamm fehlt der Artikelname. Bitte zuerst die Stammdaten ergänzen.")
    tools=sorted(article.tools,key=lambda t:t.tool_no)
    chosen=(form.get("tool_no") or "").strip()
    if not chosen and len(tools)==1:chosen=tools[0].tool_no
    linked=next((t for t in tools if t.tool_no==chosen),None)
    # Never overwrite an explicitly saved ERP/legacy tool just because a master
    # assignment changed later. It may be retained, but not newly assigned here.
    retained=bool(order and article_no==order.article and chosen and chosen==order.tool_no and Tool.query.filter_by(tool_no=chosen).first())
    if not linked and not retained:
        if not tools:raise ValueError("Dem Artikel ist noch kein Werkzeug zugeordnet. Bitte zuerst die Artikelstammdaten ergänzen.")
        raise ValueError("Bitte ein dem Artikel zugeordnetes Werkzeug auswählen. Bei mehreren Werkzeugen ist eine bewusste Auswahl erforderlich.")
    if len(chosen)>50:raise ValueError("Werkzeugnummer ist länger als das bestehende Auftragsfeld (50 Zeichen). Bitte Stammdaten prüfen.")
    data.update(article=article.article_no,article_name=article.article_name,tool_no=chosen,
        target_qty=parse_quantity(form.get("target_qty")),cycle_time_s=parse_cycle_time(form.get("cycle_time_s")))
    return data

def form_context(order=None,form=None,prefill=""):
    form=form or {}
    articles=Article.query.options(selectinload(Article.tools)).order_by(Article.article_no).all()
    values={key:getattr(order,key,None) if order else "" for key in
        ("order_no","article","article_name","tool_no","description","location","target_qty","cycle_time_s","status")}
    if not order and prefill:values["article"]=prefill
    for key in values:
        if key!="article_name" and key in form:values[key]=form[key]
    values["article"]=(values["article"] or "").strip()
    selected=next((a for a in articles if a.article_no==values["article"]),None)
    catalog={a.article_no:{"name":a.article_name,"cycle":valid_cycle_time(a.cycle_time_s),
        "tools":[{"number":t.tool_no,"name":t.name or "","legacy":False} for t in sorted(a.tools,key=lambda t:t.tool_no)]} for a in articles}
    legacy_tool=None
    if order and order.tool_no:
        legacy_tool=Tool.query.filter_by(tool_no=order.tool_no).first()
        record=catalog.get(order.article)
        if record is not None and legacy_tool and not any(t["number"]==order.tool_no for t in record["tools"]):
            record["tools"].append({"number":legacy_tool.tool_no,"name":legacy_tool.name or "","legacy":True})
    choices=catalog.get(values["article"],{}).get("tools",[])
    if not values["tool_no"] and len(choices)==1:values["tool_no"]=choices[0]["number"]
    if selected:values["article_name"]=selected.article_name
    elif not order or not order.is_project:values["article_name"]=""
    explicit=bool(str(form.get("cycle_time_s",values.get("cycle_time_s") or "")).strip())
    if not explicit and selected:values["cycle_time_s"]=valid_cycle_time(selected.cycle_time_s) or ""
    status_options=[]
    for aliases,label in ((('open','offen'),'Offen'),(('in_arbeit','running'),'In Arbeit'),(('fertig','finished','abgeschlossen'),'Fertig'),(('gesperrt','locked'),'Gesperrt'),(('storniert','cancelled','canceled'),'Storniert')):
        status_options.append((values['status'] if values['status'] in aliases else aliases[0],label))
    if values['status'] and values['status'] not in {key for key,_ in status_options}:status_options.append((values['status'],status_label(values['status'])))
    return dict(order=order,articles=articles,values=values,article_record=selected,tool_choices=choices,status_options=status_options,
        article_catalog=catalog,cycle_explicit=explicit,status_labels=STATUS_LABELS,
        managed_article_form=True,legacy_tool=legacy_tool)

def overview_records(orders):
    numbers={o.article for o in orders if o.article}
    articles={a.article_no:a for a in Article.query.options(selectinload(Article.tools)).filter(Article.article_no.in_(numbers)).all()} if numbers else {}
    tool_numbers={o.tool_no for o in orders if o.tool_no}
    tools={t.tool_no:t for t in Tool.query.filter(Tool.tool_no.in_(tool_numbers)).all()} if tool_numbers else {}
    result=[]
    for order in orders:
        article=articles.get(order.article);tool=tools.get(order.tool_no);suggested=False
        if not order.tool_no and article and len(article.tools)==1:tool=article.tools[0];suggested=True
        valid_qty=isinstance(order.target_qty,int) and order.target_qty>0
        issues=[]
        if not order.is_project:
            if not article:issues.append("Artikelstamm fehlt oder Artikelnummer ist nicht zugeordnet.")
            if not valid_qty:issues.append("Positive Stückzahl fehlt.")
            if not order.tool_no or not tool:issues.append("Auftragswerkzeug fehlt oder ist nicht in den Stammdaten vorhanden.")
            if not valid_cycle_time(order.cycle_time_s):issues.append("Soll-Zykluszeit fehlt.")
        result.append(dict(order=order,article=article,name=article.article_name if article else order.article_name,
            tool=tool,tool_suggested=suggested,valid_qty=valid_qty,issues=issues,status_label=status_label(order.status)))
    return result
