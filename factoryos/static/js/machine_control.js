(() => {
  'use strict';
  const dialog=document.getElementById('machine-control-dialog');
  if(dialog){
    const frame=dialog.querySelector('iframe');let changed=false;
    document.querySelectorAll('[data-machine-control-url]').forEach(button=>button.addEventListener('click',()=>{
      const url=new URL(button.dataset.machineControlUrl,location.origin);
      if(url.origin!==location.origin)return;
      if(!dialog.showModal){location.href=url.href;return;}
      changed=false;frame.src=url.href;
      const fullscreen=new URL(url);fullscreen.searchParams.delete('embedded');
      dialog.querySelector('[data-control-fullscreen]').href=fullscreen.href;
      dialog.showModal();
    }));
    dialog.querySelector('[data-control-close]').addEventListener('click',()=>dialog.close());
    dialog.addEventListener('close',()=>{frame.src='about:blank';if(changed)location.reload();});
    window.addEventListener('message',event=>{
      if(event.origin===location.origin && event.source===frame.contentWindow && event.data?.type==='factoryos-machine-changed')changed=true;
    });
  }
  const form=document.getElementById('control-command-form');
  if(!form)return;
  const search=document.getElementById('control-order-search');
  const select=document.getElementById('control-order');
  search?.addEventListener('input',()=>{
    const term=search.value.toLocaleLowerCase();
    [...select.options].forEach(option=>{option.hidden=!!option.value && !option.text.toLocaleLowerCase().includes(term);});
  });
  let submitting=false;
  form.addEventListener('submit',event=>{
    if(submitting){event.preventDefault();return;}
    const label=event.submitter?.dataset.label;
    if(!label || !confirm(`${document.querySelector('h1').textContent}: ${label}?`)){event.preventDefault();return;}
    submitting=true;
    // Keep the clicked button enabled until form serialization includes its action.
    window.setTimeout(()=>form.querySelectorAll('button').forEach(b=>b.disabled=true),0);
  });
  if(document.body.dataset.changed==='1' && parent!==window)parent.postMessage({type:'factoryos-machine-changed'},location.origin);
  async function checkState(){
    if(document.hidden||submitting)return;
    try{
      const response=await fetch(document.body.dataset.stateUrl,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
      if(!response.ok||!response.headers.get('content-type')?.includes('application/json')){
        form.querySelectorAll('button').forEach(b=>b.disabled=true);
        document.getElementById('control-stale').hidden=false;return;
      }
      const data=await response.json();
      if(data.revision!==document.body.dataset.revision){
        if(parent!==window)parent.postMessage({type:'factoryos-machine-changed'},location.origin);
        document.getElementById('control-stale').hidden=false;
        form.querySelectorAll('button').forEach(b=>b.disabled=true);
      }
    }catch(_){
      // Offline commands are never queued or replayed automatically.
      document.getElementById('control-stale').textContent='Verbindung unterbrochen. Bitte neu laden und Maschinenstand prüfen.';
      document.getElementById('control-stale').hidden=false;
      form.querySelectorAll('button').forEach(b=>b.disabled=true);
    }
  }
  window.setInterval(checkState,15000);
})();
