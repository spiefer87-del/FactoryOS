document.addEventListener('DOMContentLoaded',()=>{
    const article=document.getElementById('article-select'),search=document.getElementById('article-search'),tool=document.getElementById('tool-select');if(!article||!search||!tool)return;
    const status=document.getElementById('article-search-status'),toolStatus=document.getElementById('tool-selection-status');
    const options=Array.from(article.options).filter(o=>o.value).map(o=>o.cloneNode(true));
    const normalize=text=>text.trim().toLocaleLowerCase('de');
    const picker=typeof TomSelect==='function'?new TomSelect('#tool-select',{valueField:'id',labelField:'text',searchField:'text',placeholder:'Werkzeug wählen...'}):null;
    let sequence=0;
    function clearTools(){if(picker){picker.clear();picker.clearOptions();picker.disable();}else{tool.replaceChildren(new Option('-- zuerst Artikel wählen --',''));tool.disabled=true;}}
    async function loadTools(){const current=++sequence,id=article.value;clearTools();toolStatus.textContent='';if(!id)return;toolStatus.textContent='Zugeordnete Werkzeuge werden geladen …';
        try{const response=await fetch('/quality/inspection-plans/tools-by-article/'+encodeURIComponent(id));if(!response.ok)throw new Error('Laden fehlgeschlagen');const data=await response.json();if(current!==sequence)return;
            if(picker){picker.addOptions(data);if(data.length)picker.enable();}else{tool.replaceChildren(new Option('-- Werkzeug wählen --',''));data.forEach(row=>tool.add(new Option(row.text,row.id)));tool.disabled=!data.length;}
            toolStatus.textContent=data.length?'':'Diesem Artikel sind keine Werkzeuge zugeordnet.';
        }catch(error){if(current===sequence)toolStatus.textContent='Werkzeuge konnten nicht geladen werden. Artikel bitte erneut auswählen oder Seite neu laden.';}
    }
    search.addEventListener('input',()=>{const query=normalize(search.value),previous=article.value,filtered=query.length<2?options:options.filter(o=>normalize(o.textContent).includes(query));
        article.replaceChildren(new Option('-- Artikel wählen --',''),...filtered.map(o=>o.cloneNode(true)));article.value=filtered.some(o=>o.value===previous)?previous:'';
        status.textContent=query.length<2?'Ab zwei Zeichen wird die Artikelauswahl gefiltert.':filtered.length?filtered.length+' passende Artikel – bitte auswählen.':'Keine passenden Artikel gefunden. Suche ändern oder leeren.';
        if(article.value!==previous)loadTools();
    });
    article.addEventListener('change',loadTools);loadTools();
    // A disabled tool field must not permit submitting an incomplete selection.
    article.form.addEventListener('submit',event=>{if(!article.value||!tool.value){event.preventDefault();toolStatus.textContent='Bitte Artikel und zugehöriges Werkzeug auswählen.';}});
});
