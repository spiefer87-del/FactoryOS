document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('[data-source-search]').forEach(form=>{
  const input=form.querySelector('[data-source-query]'),kind=form.querySelector('[name=kind]'),select=form.querySelector('[name=target_id]'),status=form.querySelector('[data-source-status]');let timer,revision=0;
  const clear=()=>{select.replaceChildren(new Option('Bitte Suchergebnis wählen',''));};
  const search=()=>{clearTimeout(timer);const current=++revision;clear();const q=input.value.trim();if(q.length<2){status.textContent='Mindestens zwei Zeichen eingeben.';return;}
   timer=setTimeout(async()=>{status.textContent='Suche …';try{const url=new URL(form.dataset.sourceSearch,location.href);url.searchParams.set('q',q);url.searchParams.set('kind',kind.value);const response=await fetch(url,{credentials:'same-origin'});if(!response.ok)throw Error('Keine Suchberechtigung oder Sitzung abgelaufen.');const data=await response.json();if(current!==revision)return;data.results.forEach(row=>select.add(new Option(row.label,row.id)));status.textContent=data.results.length?data.results.length+' Treffer (maximal 30).':'Keine passenden Vorgänge gefunden.';}catch(error){if(current===revision)status.textContent=error.message;}},250);
  };input.addEventListener('input',search);kind.addEventListener('change',search);
 });
});
