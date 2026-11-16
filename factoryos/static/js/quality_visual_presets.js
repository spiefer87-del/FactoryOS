document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('[data-apply-visual-preset]').forEach(button=>{
        button.addEventListener('click',()=>{
            const form=button.closest('form'),select=form.querySelector('[data-visual-preset]'),status=form.querySelector('[data-preset-status]');
            const option=select.selectedOptions[0];if(!option||!option.dataset.values){status.textContent='Bitte zuerst einen Fehler auswählen.';select.focus();return;}
            const values=JSON.parse(option.dataset.values),keys=['name','requirement','method'];
            if(keys.some(key=>form.elements[key].value.trim())&&!window.confirm('Die drei Eingabefelder enthalten bereits Angaben. Durch die Vorlage ersetzen?'))return;
            keys.forEach(key=>{form.elements[key].value=values[key];form.elements[key].dispatchEvent(new Event('input',{bubbles:true}));});
            status.textContent='Vorlage übernommen – noch nicht gespeichert. Bitte prüfen und anpassen.';form.elements.name.focus();
        });
    });
});
