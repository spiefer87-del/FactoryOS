(() => {
  'use strict';
  document.querySelectorAll('[data-order-search]').forEach(input=>input.addEventListener('input',()=>{
    const select=input.closest('form').querySelector('[name="order_id"]');
    [...select.options].forEach(option=>option.hidden=!!option.value&&!option.text.toLocaleLowerCase().includes(input.value.toLocaleLowerCase()));
  }));
  document.getElementById('planning-filter')?.addEventListener('input',event=>{
    const term=event.target.value.toLocaleLowerCase();
    document.querySelectorAll('.planning-lane').forEach(lane=>{
      const content=[lane.querySelector('header').textContent,...[...lane.querySelectorAll('.planning-entry')].map(e=>e.textContent)].join(' ').toLocaleLowerCase();
      lane.hidden=!content.includes(term);
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{
    if(!confirm(form.dataset.confirm))event.preventDefault();
  }));
  let dragged=null;let sourceMachine=null;
  document.querySelectorAll('.planning-queue').forEach(queue=>{
    queue.addEventListener('dragstart',event=>{
      const item=event.target.closest('.planning-entry[draggable="true"]');
      if(!item||event.target.closest('input,select,textarea,button,a')){event.preventDefault();return;}
      dragged=item;sourceMachine=queue.dataset.machineId;item.classList.add('dragging');event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',item.dataset.entryId);
    });
    queue.addEventListener('dragover',event=>{if(dragged)event.preventDefault();});
    queue.addEventListener('drop',event=>{
      if(!dragged)return;event.preventDefault();
      if(sourceMachine!==queue.dataset.machineId){
        const form=document.getElementById('planning-drag-transfer');
        form.querySelector('[name="machine_id"]').value=sourceMachine;
        form.querySelector('[name="entry_id"]').value=dragged.dataset.entryId;
        form.querySelector('[name="target_machine_id"]').value=queue.dataset.machineId;
        form.requestSubmit?form.requestSubmit():form.submit();return;
      }
      const target=event.target.closest('.planning-entry');
      if(target&&target!==dragged){
        const below=event.clientY>target.getBoundingClientRect().top+target.offsetHeight/2;
        queue.insertBefore(dragged,below?target.nextSibling:target);
        const form=queue.closest('.planning-lane').querySelector('.planning-reorder');
        form.querySelector('[name="ordered_ids"]').value=JSON.stringify([...queue.querySelectorAll('.planning-entry')].map(e=>Number(e.dataset.entryId)));
        form.requestSubmit?form.requestSubmit():form.submit();
      }
    });
    queue.addEventListener('dragend',()=>{dragged?.classList.remove('dragging');dragged=null;});
  });
})();
