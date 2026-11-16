/* Progressive enhancement only; all master, acknowledgement and workflow checks are server-side too. */
(() => {
  'use strict';
  const bootNode=document.getElementById('control-selection-data');if(!bootNode)return;
  const data=JSON.parse(bootNode.textContent),byId=id=>document.getElementById(id);
  const form=byId('control-command-form'),order=byId('control-order'),tool=byId('control-tool');
  const check=byId('control-tool-confirmed'),confirmedNo=byId('control-tool-confirmation-no');
  const label=byId('control-tool-confirm-label'),error=byId('control-selection-error');
  const tools=new Map(data.tools.map(t=>[t.number,t]));
  const info=()=>data.orders[order.value]||{};
  function reset(){check.checked=false;confirmedNo.value='';error.hidden=true;}
  function describe(){label.textContent='Werkzeug '+(tool.value.trim()||'auswählen')+' vor Ort geprüft – diese Nummer bewusst übernehmen.';}
  function showProposal(proposal){
    byId('control-proposal').textContent=proposal?'Werkzeugvorschlag: '+proposal.number+' · '+proposal.name+' · '+proposal.source:
      'Kein eindeutiger Werkzeugvorschlag. Bitte vorhandene Werkzeugnummer auswählen oder eingeben.';
  }
  function update(){
    const current=info(),proposal=current.proposal||data.stock;
    tool.value=proposal?.number||'';reset();describe();showProposal(proposal);
    byId('control-sampling-note').textContent=current.note||'Ohne Auftrag: vorhandenes Werkzeug für den Rüstvorgang wählen.';
    const link=byId('control-sampling-prepare');
    link.hidden=!(current.sampling&&!current.ready&&current.prepare_url);
    if(!link.hidden)link.href=current.prepare_url;else link.removeAttribute('href');
  }
  order.addEventListener('change',update);
  tool.addEventListener('input',()=>{reset();describe();});
  tool.addEventListener('change',()=>{reset();describe();});
  check.addEventListener('change',()=>{confirmedNo.value=check.checked?tool.value.trim():'';error.hidden=true;});
  byId('control-use-stock')?.addEventListener('click',event=>{
    event.preventDefault();tool.value=data.stock?.number||'';reset();describe();showProposal(data.stock);tool.focus();
  });
  function fail(event,message,target){event.preventDefault();error.textContent=message;error.hidden=false;target.focus();error.scrollIntoView?.({behavior:'smooth',block:'center'});}
  form.addEventListener('submit',event=>{
    const action=event.submitter?.value;if(!['start','setup','unsetup'].includes(action))return;
    tool.value=tool.value.trim();
    if(!tools.has(tool.value)){fail(event,'Werkzeugnummer: bitte eine vorhandene Nummer aus dem Werkzeugstamm eingeben oder auswählen.',tool);return;}
    if(!check.checked||confirmedNo.value!==tool.value){fail(event,'Werkzeug '+tool.value+': bitte die geprüfte Nummer mit dem Haken bestätigen.',check);return;}
    if(action!=='unsetup'&&info().sampling&&!info().ready){
      fail(event,'Diese Musterung muss zuerst bewusst vorbereitet und dieser Maschine zugeordnet werden. Ohne Bearbeitungsrecht bitte eine berechtigte Person hinzuziehen.',byId('control-sampling-prepare').hidden?order:byId('control-sampling-prepare'));
    }
  });
  // Keep values from an unsuccessful submission; never overwrite them on page load.
  check.checked=false;confirmedNo.value='';describe();
})();
