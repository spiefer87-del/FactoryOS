document.addEventListener('DOMContentLoaded',()=>{
    const wrapper=document.getElementById('quality-plan-list-wrapper');if(!wrapper)return;
    const table=wrapper.querySelector('table'),toggles=[...wrapper.querySelectorAll('[data-quality-column]')];
    const defaults=Object.fromEntries(toggles.map(t=>[t.value,t.checked]));
    const key='factoryos.quality.columns.tab.'+wrapper.dataset.user;
    let visible={...defaults};try{const saved=JSON.parse(sessionStorage.getItem(key)||'null');if(saved&&typeof saved==='object')toggles.forEach(t=>{if(typeof saved[t.value]==='boolean')visible[t.value]=saved[t.value];});}catch(_){/* Browser storage optional. */}
    function apply(){visible.tool_no=true;visible.actions=true;toggles.forEach(t=>{t.checked=visible[t.value];table.querySelectorAll('[data-col="'+t.value+'"]').forEach(cell=>cell.hidden=!t.checked);});}
    function save(){apply();try{sessionStorage.setItem(key,JSON.stringify(visible));}catch(_){/* Current page remains usable. */}}
    toggles.forEach(t=>t.addEventListener('change',()=>{visible[t.value]=t.checked;save();}));
    wrapper.querySelector('#reset-quality-columns').addEventListener('click',()=>{visible={...defaults};save();});apply();
    const search=wrapper.querySelector('.fos-search'),status=wrapper.querySelector('#quality-plan-results');
    function count(){const term=search.value.trim().toLowerCase();const rows=[...table.tBodies[0].rows];const matches=rows.filter(r=>(r.dataset.searchText||'').replace(/\s+/g,' ').trim().toLowerCase().includes(term)).length;status.textContent=matches?matches+' Prüfplan/Prüfpläne gefunden.':rows.length?'Keine passenden Prüfpläne gefunden.':'Noch keine Prüfpläne vorhanden.';}
    search.addEventListener('input',count);count();
});
