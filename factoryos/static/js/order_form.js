(() => {
  'use strict';
  const data=document.getElementById('order-master-data');if(!data)return;
  const config=JSON.parse(data.textContent);
  const article=document.getElementById('order-article');
  const name=document.getElementById('order-article-name');
  const tool=document.getElementById('order-tool');
  const cycle=document.getElementById('cycle_time_s');
  const hint=document.getElementById('order-master-hint');
  const cycleHint=document.getElementById('order-cycle-hint');
  let previous=article.value.trim();let manualCycle=!!config.cycle_explicit;
  cycle.addEventListener('input',()=>manualCycle=true);
  function update(){
    const number=article.value.trim();const record=Object.prototype.hasOwnProperty.call(config.articles,number)?config.articles[number]:null;
    const oldChoice=number===previous?tool.value:'';
    name.value=record?.name||'';
    const options=record?.tools||[];
    tool.replaceChildren(new Option(options.length?'Bitte Werkzeug auswählen':'Keine Werkzeugzuordnung vorhanden',''));
    options.forEach(item=>tool.add(new Option(`${item.number} · ${item.name}${item.legacy?' (gespeicherte Auftragszuordnung)':''}`,item.number)));
    if(options.some(item=>item.number===oldChoice))tool.value=oldChoice;
    else if(options.length===1)tool.value=options[0].number;
    article.setCustomValidity(record?'':'Bitte eine vorhandene Artikelnummer aus den Stammdaten auswählen.');
    hint.textContent=!record?'Artikelnummer aus den Stammdaten auswählen.':options.length===0?'Dem Artikel fehlt eine Werkzeugzuordnung. Bitte Artikelstammdaten ergänzen.':options.length===1?'Werkzeug automatisch aus der eindeutigen Zuordnung übernommen.':'Mehrere Werkzeuge vorhanden – bitte bewusst auswählen. Eine gespeicherte Altzuordnung darf beibehalten werden.';
    const suggestion=Number(record?.cycle);
    if(!manualCycle)cycle.value=Number.isFinite(suggestion)&&suggestion>0?String(suggestion):'';
    cycleHint.textContent=Number.isFinite(suggestion)&&suggestion>0?`Artikel-Sollwert: ${suggestion} s. Der Auftragswert bleibt unabhängig und kann angepasst werden.`:'Kein gültiger Artikel-Sollwert hinterlegt. Soll-Zykluszeit bitte angeben.';
    // A server-rendered link must never keep pointing to the previously selected article.
    const link=document.getElementById('order-master-link');if(link&&number!==previous)link.hidden=true;
    previous=number;
  }
  article.addEventListener('input',update);article.addEventListener('change',update);update();
})();
