document.addEventListener('DOMContentLoaded',()=>{
    const source=document.getElementById('dashboard-catalog-data');if(!source)return;
    const data=JSON.parse(source.textContent),form=document.getElementById('dashboard-editor'),grid=document.getElementById('dashboard-preview'),status=document.getElementById('dashboard-editor-status');
    const catalog=new Map(data.catalog.map(tile=>[tile.key,tile]));let order=[...data.selected],dragged=null;
    const checks=[...form.querySelectorAll('input[name="selected"]')];
    function move(key,offset){const index=order.indexOf(key),target=index+offset;if(target<0||target>=order.length)return;[order[index],order[target]]=[order[target],order[index]];render(key,offset<0?'up':'down');}
    function button(text,label,callback){const el=document.createElement('button');el.type='button';el.textContent=text;el.setAttribute('aria-label',label);el.addEventListener('click',callback);return el;}
    function render(focusKey,focusAction){
        grid.replaceChildren();
        order.forEach((key,index)=>{
            const tile=catalog.get(key);if(!tile)return;
            const card=document.createElement('article');card.className='personal-tile personal-edit-tile';card.dataset.key=key;
            const controls=document.createElement('div');controls.className='personal-tile-controls';
            const handle=button('⠿',tile.title+' mit der Maus verschieben',()=>{});handle.draggable=true;handle.className='tile-drag-handle';
            handle.addEventListener('dragstart',event=>{dragged=key;event.dataTransfer.setData('text/plain',key);event.dataTransfer.effectAllowed='move';});handle.addEventListener('dragend',()=>{dragged=null;});
            const up=button('↑',tile.title+' nach oben',()=>move(key,-1)),down=button('↓',tile.title+' nach unten',()=>move(key,1));up.dataset.action='up';down.dataset.action='down';up.disabled=index===0;down.disabled=index===order.length-1;
            const remove=button('✕',tile.title+' entfernen',()=>{order=order.filter(id=>id!==key);render();});controls.append(handle,up,down,remove);
            const icon=document.createElement('span');icon.className='personal-tile-icon';icon.textContent=tile.icon;icon.setAttribute('aria-hidden','true');
            const title=document.createElement('h3');title.textContent=tile.title;const group=document.createElement('small');group.textContent=tile.group;
            card.append(controls,icon,group,title);card.addEventListener('dragover',event=>{if(dragged)event.preventDefault();});card.addEventListener('drop',event=>{event.preventDefault();if(!dragged||dragged===key||!order.includes(dragged))return;const sourceKey=dragged,rect=card.getBoundingClientRect(),after=event.clientY>rect.top+rect.height/2;order=order.filter(id=>id!==sourceKey);order.splice(order.indexOf(key)+(after?1:0),0,sourceKey);dragged=null;render();});grid.append(card);
        });
        checks.forEach(input=>{input.checked=order.includes(input.value);const position=form.elements['position_'+input.value];position.value=input.checked?order.indexOf(input.value)+1:99;});
        form.elements.layout.value=JSON.stringify(order);status.textContent=order.length?order.length+' Kacheln ausgewählt. Änderungen erst nach Speichern wirksam.':'Keine Kacheln ausgewählt. Dein Dashboard darf auch leer bleiben.';
        if(focusKey){const card=[...grid.children].find(el=>el.dataset.key===focusKey);const buttons=card?[...card.querySelectorAll('button[data-action]')]:[];const target=buttons.find(el=>el.dataset.action===focusAction&&!el.disabled)||buttons.find(el=>!el.disabled);if(target)target.focus();}
    }
    checks.forEach(input=>input.addEventListener('change',()=>{if(input.checked&&!order.includes(input.value))order.push(input.value);else if(!input.checked)order=order.filter(key=>key!==input.value);render();}));
    form.addEventListener('submit',()=>{form.elements.layout.value=JSON.stringify(order);});
    // Numeric positions are a no-JavaScript fallback; touch controls replace them.
    form.classList.add('dashboard-js');render();
});
