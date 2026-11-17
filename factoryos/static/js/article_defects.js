document.addEventListener('DOMContentLoaded',()=>{
 const search=document.getElementById('defect-article-search'),select=document.getElementById('defect-article');if(!search||!select)return;
 const options=[...select.options].filter(o=>o.value).map(o=>o.cloneNode(true)),status=document.getElementById('defect-article-status');
 search.addEventListener('input',()=>{const query=search.value.trim().toLocaleLowerCase('de'),previous=select.value,filtered=query.length<2?options:options.filter(o=>o.textContent.toLocaleLowerCase('de').includes(query));select.replaceChildren(new Option('Bitte auswählen',''),...filtered.map(o=>o.cloneNode(true)));select.value=filtered.some(o=>o.value===previous)?previous:'';status.textContent=filtered.length?filtered.length+' Artikel zur Auswahl.':'Keine passenden Artikel gefunden.';});
});
