document.addEventListener('DOMContentLoaded',()=>{
    const dialog=document.getElementById('warehouse-intake-dialog'),content=document.getElementById('warehouse-intake-content');if(!dialog||typeof dialog.showModal!=='function')return;
    let opener=null,busy=false,loadSequence=0;
    function close(){if(!busy){loadSequence++;dialog.close();if(opener&&opener.isConnected)opener.focus();}}
    dialog.querySelector('[data-close-intake]').addEventListener('click',close);
    dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();else{loadSequence++;if(opener&&opener.isConnected)opener.focus();}});
    async function open(row){const current=++loadSequence;opener=row;content.textContent='Lade aktuelle Auftragsdaten …';dialog.showModal();
        try{const response=await fetch(row.dataset.intakeUrl+'?partial=1',{credentials:'same-origin'});if(!response.ok||response.redirected)throw new Error();const html=await response.text();if(current!==loadSequence||!dialog.open)return;content.innerHTML=html;const field=content.querySelector('input[name="quantity"]');if(field)field.focus();}
        catch(_){if(current===loadSequence&&dialog.open)content.textContent='Die Buchungsmaske konnte nicht geladen werden. Bitte schließen und erneut versuchen.';}
    }
    document.addEventListener('click',event=>{const row=event.target.closest('[data-intake-url]');if(!row||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey)return;if(event.target.closest('input,select,textarea'))return;event.preventDefault();if(!dialog.open)open(row);});
    document.addEventListener('keydown',event=>{const row=event.target.closest('tr[data-intake-url]');if(row&&event.target===row&&['Enter',' '].includes(event.key)){event.preventDefault();if(!dialog.open)open(row);}});
    content.addEventListener('submit',async event=>{const form=event.target.closest('[data-intake-form]');if(!form)return;event.preventDefault();if(busy)return;busy=true;const button=form.querySelector('button[type=submit]');button.disabled=true;
        try{const response=await fetch(form.action+'?partial=1',{method:'POST',credentials:'same-origin',body:new FormData(form)});
            if(response.ok&&!response.redirected){const result=await response.json();window.location.assign(result.redirect);return;}
            if([409,422].includes(response.status)){content.innerHTML=await response.text();content.querySelector('[role=alert]')?.scrollIntoView({block:'nearest'});}
            else{form.querySelector('[data-intake-message]').textContent='Nicht gebucht: Sitzung oder Berechtigung prüfen und Seite neu laden.';button.disabled=false;}
        }catch(_){form.querySelector('[data-intake-message]').textContent='Antwort nicht erhalten. Bitte unverändert erneut versuchen; die Buchungskennung schützt vor Doppelbuchung.';button.disabled=false;}
        finally{busy=false;}
    });
});
