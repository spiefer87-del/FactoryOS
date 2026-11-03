(() => {
  'use strict';
  const root=document.getElementById('material-scanner');if(!root)return;
  const form=document.getElementById('material-create-form');
  const status=document.getElementById('material-scan-status');
  const review=document.getElementById('material-scan-review');
  const choices=JSON.parse(document.getElementById('material-scan-choices').textContent);
  const token=document.getElementById('material-scan-csrf').value;
  let photo=null;let blobUrl=null;let busy=false;let candidates=[];
  const allowed=new Set(['name','manufacturer','external_material_no','material_type','polymer_type','color','color_no','ral_color','delivery_form']);
  function message(text,error=false){status.textContent=text;status.className=error?'material-scan-alert':'material-scan-success';}
  function setBusy(value){busy=value;root.querySelectorAll('button,input[type="file"]').forEach(button=>button.disabled=value);root.setAttribute('aria-busy',String(value));}
  function textNode(tag,text,parent,className=''){const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;parent.append(node);return node;}
  function render(data){
    review.hidden=false;document.getElementById('material-scan-text').value=data.text;
    document.getElementById('material-scan-readability').textContent=data.readability==null?'Textbasierte Vorschläge – ohne OCR-Lesbarkeitswert.':`OCR-Lesbarkeit: ${data.readability}/100. Das ist keine Gewähr für richtige Materialdaten. Sprache: ${data.languages||''}.`;
    const notes=document.getElementById('material-scan-notes');notes.replaceChildren();
    (data.notes||[]).forEach(note=>textNode('p',note,notes,'material-scan-note'));
    const duplicates=document.getElementById('material-scan-duplicates');duplicates.replaceChildren();
    if(data.duplicate_count){
      textNode('strong','Mögliche vorhandene Materialien – vor Neuanlage prüfen:',duplicates);
      (data.duplicates||[]).forEach(item=>{
        const line=document.createElement('p');const link=textNode('a',`${item.material_no} · ${item.name}`,line);
        const target=new URL(item.url,location.origin);
        if(target.origin===location.origin){link.href=target.href;link.target='_blank';link.rel='noopener';}
        duplicates.append(line);
      });
      if(!data.duplicates?.length)textNode('p','Mögliche Dublette gefunden. Vorhandene Materialien durch eine berechtigte Person prüfen lassen.',duplicates);
    }
    duplicates.className=data.duplicate_count?'material-scan-alert':'';
    const fields=document.getElementById('material-scan-fields');fields.replaceChildren();candidates=[];
    (data.proposals||[]).filter(proposal=>allowed.has(proposal.field)).forEach(proposal=>{
      const row=document.createElement('div');row.className='material-scan-field'+(proposal.certainty==='review'?' is-uncertain':'');
      const heading=document.createElement('label');heading.className='material-scan-check';
      const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=proposal.certainty==='label';heading.append(checkbox);textNode('span',proposal.label,heading);row.append(heading);
      let input;
      if(choices[proposal.field]){input=document.createElement('select');Object.entries(choices[proposal.field]).forEach(([value,label])=>input.add(new Option(label,value)));}
      else{input=document.createElement('input');input.type='text';input.maxLength=proposal.field==='name'?200:proposal.field==='manufacturer'?150:100;}
      input.value=proposal.value;input.setAttribute('aria-label',proposal.label);row.append(input);
      textNode('small','Gelesen: '+proposal.evidence,row);
      if(proposal.note)textNode('small',proposal.note,row);
      fields.append(row);candidates.push({proposal,checkbox,input});
    });
    if(!candidates.length)textNode('p','Keine eindeutigen Stammdatenfelder erkannt. Foto erneut aufnehmen oder den Etiketttext korrigieren.',fields,'material-scan-alert');
    document.getElementById('material-scan-apply').disabled=!candidates.length;
  }
  async function request(url,data){
    setBusy(true);message('Erkennung läuft – bitte kurz warten. Es wird noch kein Material gespeichert.');
    try{
      data.append('access_csrf',token);
      const response=await fetch(url,{method:'POST',body:data,credentials:'same-origin',cache:'no-store',headers:{'X-Access-CSRF':token}});
      if(!response.headers.get('content-type')?.includes('application/json'))throw new Error(response.status===413?'Foto ist zu groß. Bitte kleineres Foto verwenden.':'Anmeldung/Formular möglicherweise abgelaufen. Bitte Seite neu laden; Kamera-/Uploadberechtigung prüfen.');
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Erkennung fehlgeschlagen. Bitte erneut versuchen.');
      render(result);message('Vorschläge bereit. Bitte einzeln prüfen und übernehmen.');
    }catch(error){candidates=[];message(error.message||'Verbindung unterbrochen. Es wurde kein Material angelegt.',true);}
    finally{setBusy(false);document.getElementById('material-scan-apply').disabled=!candidates.length;}
  }
  function scan(){if(!photo||busy)return;const data=new FormData();data.append('photo',photo,photo.name);request(root.dataset.scanUrl,data);}
  function choose(event){
    const selected=event.target.files[0];if(!selected||busy)return;
    if(selected.size>10*1024*1024){message('Foto ist größer als 10 MB. Bitte eine kleinere Aufnahme wählen.',true);return;}
    photo=selected;review.hidden=true;candidates=[];
    if(blobUrl)URL.revokeObjectURL(blobUrl);blobUrl=URL.createObjectURL(photo);
    document.getElementById('material-scan-preview').src=blobUrl;document.getElementById('material-scan-image').hidden=false;scan();
    event.target.value='';
  }
  document.getElementById('material-scan-camera').addEventListener('change',choose);
  root.querySelectorAll('label[role="button"]').forEach(label=>label.addEventListener('keydown',event=>{
    if(event.key==='Enter'||event.key===' '){event.preventDefault();label.querySelector('input[type="file"]').click();}
  }));
  document.getElementById('material-scan-file').addEventListener('change',choose);
  document.getElementById('material-scan-again').addEventListener('click',scan);
  document.getElementById('material-scan-parse').addEventListener('click',()=>{const data=new FormData();data.append('text',document.getElementById('material-scan-text').value);request(root.dataset.textUrl,data);});
  document.getElementById('material-scan-apply').addEventListener('click',()=>{
    const selected=candidates.filter(item=>item.checkbox.checked&&item.input.value.trim());
    if(!selected.length){message('Bitte mindestens eine erkannte Angabe auswählen.',true);return;}
    const overwrite=selected.filter(item=>{const field=form.elements.namedItem(item.proposal.field);return field&&field.value&&field.value!==item.input.value;});
    if(overwrite.length&&!confirm(`${overwrite.length} bereits ausgefüllte Angaben durch die geprüften Vorschläge ersetzen?`))return;
    selected.sort((a,b)=>(a.proposal.field==='material_type'?-1:0)-(b.proposal.field==='material_type'?-1:0)).forEach(item=>{
      const field=form.elements.namedItem(item.proposal.field);if(!field)return;
      field.value=item.input.value.trim();field.dispatchEvent(new Event('change',{bubbles:true}));
    });
    message('Geprüfte Angaben übernommen. Interne Materialnummer und alle Pflichtfelder ergänzen, dann unten „Material anlegen“ drücken. Noch nichts gespeichert.');
    form.scrollIntoView({behavior:'smooth',block:'start'});
  });
  window.addEventListener('pagehide',()=>{if(blobUrl)URL.revokeObjectURL(blobUrl);});
})();
