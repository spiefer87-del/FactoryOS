document.addEventListener('DOMContentLoaded',()=>{
 const search=document.getElementById('defect-article-search'),select=document.getElementById('defect-article'),tool=document.getElementById('defect-tool');
 const data=JSON.parse(document.getElementById('defect-article-tools').textContent);
 const article=()=>select?select.value:document.querySelector('[name=article_id]').value;
 const refreshTools=()=>{const previous=tool.value,rows=data[article()]||[];
  tool.replaceChildren(new Option('Keine Werkzeugangabe',''),...rows.map(t=>new Option(t.number,t.number)));
  if(rows.some(t=>t.number===previous))tool.value=previous;
  else if(!select&&previous)tool.add(new Option(previous+' (historische Angabe)',previous,true,true));
 };
 refreshTools();if(!search||!select)return;
 const options=[...select.options].filter(o=>o.value).map(o=>o.cloneNode(true)),status=document.getElementById('defect-article-status');
 select.addEventListener('change',refreshTools);
 search.addEventListener('input',()=>{
  const query=search.value.trim().toLocaleLowerCase('de'),previous=select.value;
  const matchesTool=t=>(t.number+' '+t.external).toLocaleLowerCase('de').includes(query);
  const filtered=query.length<2?options:options.filter(o=>(o.textContent.toLocaleLowerCase('de').includes(query)||(data[o.value]||[]).some(matchesTool)));
  select.replaceChildren(new Option('Bitte auswählen',''),...filtered.map(o=>o.cloneNode(true)));
  select.value=filtered.some(o=>o.value===previous)?previous:'';
  if(query.length>=2&&filtered.length===1)select.value=filtered[0].value;
  refreshTools();
  const matched=(data[select.value]||[]).filter(matchesTool);
  if(query.length>=2&&matched.length===1)tool.value=matched[0].number;
  status.textContent=filtered.length===1?'Ein Artikel gefunden – Zuordnung bitte prüfen.':filtered.length?filtered.length+' Artikel zur Auswahl; bitte den richtigen Artikel wählen.':'Keine passenden Artikel gefunden.';
 });
});
