document.addEventListener("DOMContentLoaded",function(){
    "use strict";
    const table=document.getElementById("tools-table");if(!table)return;
    const prefs=window.FactoryOSPreferences;
    const toggles=Array.from(document.querySelectorAll("[data-column-toggle]"));
    const cells=Array.from(table.querySelectorAll("[data-col]"));
    const status=document.getElementById("tool-view-status");
    const legacyButton=document.getElementById("importLegacyToolColumns");
    const defaults=Object.fromEntries(toggles.map(t=>[t.value,t.dataset.defaultVisible==="true"]));defaults.actions=true;defaults.tool_no=true;
    const visible=prefs?prefs.get("tools.columns"):{...defaults};let sequence=0;const unsaved={};
    function apply(){visible.tool_no=true;visible.actions=true;toggles.forEach(t=>{t.checked=visible[t.value];t.disabled=t.value==="tool_no";});cells.forEach(c=>{c.style.display=visible[c.dataset.col]?"":"none";});}
    function save(patch){Object.assign(unsaved,patch);const pending={...unsaved};const current=++sequence;apply();if(!prefs){status.textContent="Nicht gespeichert. Bitte neu laden.";return;}status.textContent="Wird im Benutzerkonto gespeichert …";
        prefs.save("tools.columns",pending).then(()=>{Object.entries(pending).forEach(([key,value])=>{if(unsaved[key]===value)delete unsaved[key];});if(current===sequence){status.textContent="Spaltenauswahl im Benutzerkonto gespeichert.";legacyButton.hidden=true;}}).catch(error=>{if(current===sequence)status.textContent="Nicht gespeichert: "+error.message+" Bitte erneut auswählen.";});}
    toggles.forEach(t=>t.addEventListener("change",()=>{visible[t.value]=t.checked;save({[t.value]:t.checked});}));
    document.getElementById("resetToolColumns").addEventListener("click",()=>{Object.assign(visible,defaults);save({...visible});});
    status.textContent=prefs?"Spaltenauswahl aus deinem Benutzerkonto geladen.":"Kontoeinstellungen nicht geladen. Bitte neu laden.";apply();
    // The former tool key was shared by all users on a browser. Never import silently.
    if(prefs&&!prefs.has("tools.columns")){
        try{const legacy=JSON.parse(window.localStorage.getItem("factoryos.tools.list.visibleColumns")||"null");
            if(Array.isArray(legacy)&&legacy.length){legacyButton.hidden=false;legacyButton.addEventListener("click",()=>{
                if(!window.confirm("Diese bisherige Browseransicht war nicht benutzerbezogen. In dein eigenes Konto übernehmen?"))return;
                Object.keys(visible).forEach(key=>{visible[key]=legacy.includes(key);});visible.tool_no=true;visible.actions=true;save({...visible});
            });}
        }catch(_){/* Keep server defaults. */}
    }
});
