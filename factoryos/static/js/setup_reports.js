(() => {
  'use strict';
  const host=document.getElementById('sr-wizard');if(!host)return;
  const boot=JSON.parse(document.getElementById('sr-boot').textContent);
  let data=structuredClone(boot.data),context=structuredClone(boot.context),version=boot.version;
  let contextToken=boot.context_token;
  let step=0,dirty=false,busy=false,editable=boot.editable,articleDefaults=false;
  const csrf=document.getElementById('sr-csrf').value;
  const byId=id=>document.getElementById(id);
  const values=data.values||(data.values={}),profiles=data.profiles||(data.profiles={});
  const selectors={};
  let issues=[];
  const fieldTargets=new Map(),contextTargets=new Map();
  const targetKey=g=>JSON.stringify([g.field||null,g.profile||null,g.row??null,g.column||null,g.context||null]);
  function bindTarget(control,container,location){
    const hint=node('p',null,container,'sr-field-error');hint.hidden=true;
    hint.id='sr-error-'+[location.field||location.profile||location.context,location.row??'',location.column||''].join('-');
    const map=location.context?contextTargets:fieldTargets;
    map.set(targetKey(location),{control,hint});
    for(const event of ['input','change'])control.addEventListener(event,()=>{
      issues=issues.filter(g=>targetKey(g)!==targetKey(location));paintErrors();
    });
  }
  function locate(g){
    const map=g.context?contextTargets:fieldTargets;
    return map.get(targetKey(g))||map.get(targetKey({...g,column:null}))||map.get(targetKey({...g,row:null,column:null}));
  }
  function goToIssue(g){
    step=Math.max(0,boot.steps.findIndex(s=>s[0]===g.step));render();
    const target=locate(g)?.control;
    (target||byId('sr-errors')).scrollIntoView?.({behavior:'smooth',block:'center',inline:'center'});
    target?.focus({preventScroll:true});
  }
  function paintErrors(){
    for(const {control,hint} of [...fieldTargets.values(),...contextTargets.values()]){
      control.removeAttribute('aria-invalid');control.removeAttribute('aria-describedby');hint.hidden=true;
    }
    for(const g of issues){const entry=locate(g);if(!entry)continue;
      entry.control.setAttribute('aria-invalid','true');entry.control.setAttribute('aria-describedby',entry.hint.id);
      entry.hint.textContent=g.message||g.label;entry.hint.hidden=false;
    }
    const box=byId('sr-errors');box.replaceChildren();box.hidden=!issues.length;
    if(issues.length){
      node('h2','Bitte Angaben prüfen – nicht gespeichert',box);
      node('p','Deine Eingaben bleiben erhalten. Klicke auf den Hinweis, um zum betroffenen Feld zu springen.',box);
      const list=node('ul',null,box);
      for(const g of issues){const title=g.step_label||boot.steps.find(s=>s[0]===g.step)?.[1]||'Einstellbericht';
        action(node('li',null,list),title+' → '+g.label+(g.message?' – '+g.message:''),()=>goToIssue(g));
      }
    }
    [...byId('sr-steps').children].forEach((button,i)=>{
      const count=issues.filter(g=>g.step===boot.steps[i][0]).length;
      button.dataset.errors=String(count);button.setAttribute('aria-label',boot.steps[i][1]+(count?' – '+count+' Fehler':''));
    });
  }
  function failure(error){
    issues=error.issues||[];
    if(issues.length)goToIssue(issues[0]);
    paintErrors();
    msg(error.message,true);
    if(!issues.length)byId('sr-status').scrollIntoView?.({behavior:'smooth',block:'center'});
  }
  const statusViews=new WeakMap();
  const syncStatus=item=>statusViews.get(item)?.();
  const fresh=unit=>({value:'',unit,status:'open',origin:'manual',reason:'',photo_id:null});
  for(const [key,spec] of Object.entries(boot.fields))values[key]||=fresh(spec.unit);
  for(const key of Object.keys(boot.profiles))profiles[key]||={rows:[],status:'open',reason:'',origin:'manual'};
  function node(tag,text,parent,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;if(parent)parent.append(n);return n;}
  function msg(text,error=false){const box=byId('sr-status');box.textContent=text;box.className=error?'sr-error':'sr-success';}
  function changed(){dirty=true;}
  function setBusy(state){busy=state;host.setAttribute('aria-busy',String(state));host.querySelectorAll('button,input,select,textarea').forEach(n=>n.disabled=state||!editable);}
  async function api(url,payload,form=false){
    const response=await fetch(url,{method:'POST',credentials:'same-origin',cache:'no-store',headers:form?{'X-Access-CSRF':csrf}:{'Content-Type':'application/json','X-Access-CSRF':csrf},body:form?payload:JSON.stringify(payload)});
    if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('Anmeldung, Berechtigung oder Formular prüfen. Eingaben bleiben hier erhalten; vor Neuladen sichern.');
    const result=await response.json();if(!response.ok){const error=new Error(result.error||'Vorgang fehlgeschlagen. Eingaben bleiben erhalten.');error.issues=result.errors||result.gaps||[];throw error;}return result;
  }
  function ids(){return Object.fromEntries(Object.entries(selectors).map(([key,n])=>[key,n.value]));}
  function select(parent,options,value,callback){
    const s=node('select',null,parent);for(const [val,label] of options)s.add(new Option(label,val));s.value=value??'';
    s.addEventListener('change',()=>{callback(s.value);changed();});return s;
  }
  function input(parent,value,callback,kind='text'){
    const n=node('input',null,parent);n.type='text';n.value=value??'';if(kind==='number')n.inputMode='decimal';
    n.addEventListener('input',()=>{callback(n.value);changed();});return n;
  }
  function action(parent,label,callback,cls='btn-secondary'){
    const b=node('button',label,parent,cls);b.type='button';b.addEventListener('click',callback);return b;
  }
  function statusControl(parent,item,label='Angabe',location={}){
    const tools=node('div',null,parent,'sr-confirm-controls');
    const checkedLabel=node('label',null,tools,'sr-check');
    const checked=node('input',null,checkedLabel);checked.type='checkbox';checked.dataset.status='confirmed';checked.setAttribute('aria-label',label+' geprüft');node('span','Geprüft',checkedLabel);
    const naLabel=node('label',null,tools,'sr-check');
    const na=node('input',null,naLabel);na.type='checkbox';na.dataset.status='na';na.setAttribute('aria-label',label+' nicht zutreffend');node('span','Nicht zutreffend',naLabel);
    const reason=input(parent,item.reason||'',v=>item.reason=v);reason.placeholder='Begründung für nicht zutreffend';reason.maxLength=800;
    if(location.field||location.profile)bindTarget(reason,parent,{...location,column:'reason'});
    function refresh(){checked.checked=item.status==='confirmed';na.checked=item.status==='na';reason.hidden=item.status!=='na';if(parent.dataset.parameter)parent.className=checked.checked?'sr-confirmed':'sr-pending';}
    statusViews.set(item,refresh);refresh();
    checked.addEventListener('change',()=>{
      if(checked.checked&&('rows' in item?!item.rows.length:!String(item.value||'').trim())){
        checked.checked=false;const message='Bitte zuerst einen Wert bzw. Profilstufen erfassen. Für nicht verwendete Angaben „Nicht zutreffend“ wählen und begründen.';
        failure({message:label+': '+message,issues:[{...location,label,message,step:(boot.fields[location.field]||boot.profiles[location.profile])?.step||boot.steps[step][0]}]});return;
      }
      item.status=checked.checked?'confirmed':'open';if(checked.checked){item.reason='';reason.value='';}refresh();changed();
    });
    na.addEventListener('change',()=>{item.status=na.checked?'na':'open';refresh();changed();if(na.checked)reason.focus();});
  }
  function unitControl(parent,item,unit,onChange=()=>{}){
    if(!unit)return;
    if(boot.units[unit])select(parent,boot.units[unit].map(v=>[v,v]),item.unit||unit,v=>{item.unit=v;item.status='open';syncStatus(item);onChange();});
    else node('span',unit,parent,'sr-note');
  }
  function origin(parent,item){
    node('small',(boot.origins[item.origin]||'Handeingabe')+(item.evidence?' · '+item.evidence:''),parent,'sr-origin');
    if(item.photo_id){const a=node('a','Quellfoto '+item.photo_id,parent,'sr-link');a.href=boot.photo_base.replace(/\/0$/, '/'+item.photo_id);a.target='_blank';a.rel='noopener';}
  }
  function renderSelectors(){
    for(const {control,hint} of contextTargets.values()){control.removeAttribute('aria-invalid');control.removeAttribute('aria-describedby');hint.remove?.();}
    contextTargets.clear();
    const box=byId('sr-selectors');box.replaceChildren();
    const definitions=[['machine_id','Maschine','machines'],['article_id','Artikel dieses Werkzeugs','articles'],['material_id','Hauptrohstoff','materials'],['masterbatch_id','Farbbatch (optional)','materials']];
    for(const [key,label,collection] of definitions){
      const wrap=node('label',label,box);
      let list=boot.choices[collection]||[];
      if(key==='masterbatch_id')list=list.filter(m=>m.category==='masterbatch');
      if(key==='material_id')list=list.filter(m=>m.category!=='masterbatch');
      // Keep a historical selection visible if the master was removed or permissions changed.
      const current=context[key];if(current&&!list.some(m=>m.id===current))list=[...list,{id:current,label:'Gespeicherte Zuordnung #'+current+' - Stammdatenzugriff prüfen'}];
      selectors[key]=select(wrap,[['','Bitte auswählen / keine Zuordnung'],...list.map(i=>[String(i.id),i.label])],current,()=>{
        data.context_confirmed=false;byId('sr-context-confirm').checked=false;
        msg('Zuordnung geändert. Bitte „Stammdatenvorschläge laden“ drücken und anschließend bestätigen.',true);
      });
      bindTarget(selectors[key],wrap,{context:key});
    }
    bindTarget(byId('sr-context-confirm'),byId('sr-identities'),{context:'context_confirmed'});
    selectors.article_id.addEventListener('change',()=>{selectors.material_id.value='';selectors.masterbatch_id.value='';articleDefaults=true;});
    selectors.material_id.addEventListener('change',()=>{articleDefaults=false;});
    selectors.masterbatch_id.addEventListener('change',()=>{articleDefaults=false;});
  }
  byId('sr-context-confirm').checked=!!data.context_confirmed;
  byId('sr-context-confirm').addEventListener('change',e=>{data.context_confirmed=e.target.checked;changed();});
  byId('sr-context').addEventListener('click',async()=>{
    if(busy||!editable)return;
    if(!confirm('Stammdaten neu abgleichen? Bisherige Stammdatenvorschläge werden erneuert und müssen erneut bestätigt werden. Eigene Parameter bleiben erhalten.'))return;
    setBusy(true);
    try{
      const selected=ids();
      if(articleDefaults){if(!selected.material_id)delete selected.material_id;if(!selected.masterbatch_id)delete selected.masterbatch_id;}
      const result=await api(boot.context_url,{ids:selected});
      const associationChanged=['machine_id','article_id','material_id','masterbatch_id'].some(key=>context[key]!==result.context[key]);
      context=result.context;contextToken=result.context_token;boot.choices=result.choices;articleDefaults=false;
      issues=issues.filter(g=>!g.context);
      for(const [key,item] of Object.entries(values)){
        if(['master','recommendation'].includes(item.origin))values[key]=result.values[key]||fresh(boot.fields[key].unit);
      }
      for(const [key,item] of Object.entries(result.values)){
        if(!values[key]?.value||['master','recommendation'].includes(values[key].origin)||['tool_no','machine_no','article_no','material_no','batch_no'].includes(key))values[key]=item;
      }
      if(associationChanged){
        Object.values(values).forEach(item=>item.status='open');
        Object.values(profiles).forEach(item=>item.status='open');
      }
      data.context_confirmed=false;byId('sr-context-confirm').checked=false;changed();renderSelectors();render();
      msg('Stammdatenvorschläge geladen. Jeden übernommenen Wert und die Zuordnungen bitte bestätigen. Eigene abweichende Werte bleiben zur Prüfung stehen.');
    }catch(error){setBusy(false);failure(error);}finally{setBusy(false);}
  });
  const nav=byId('sr-steps');
  boot.steps.forEach(([key,title],index)=>action(nav,`${index+1}. ${title}`,()=>{step=index;render();}));
  function render(){
    fieldTargets.clear();
    const key=boot.steps[step][0];
    [...nav.children].forEach((b,i)=>{if(i===step)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});
    byId('sr-identities').hidden=key!=='identity';byId('sr-entry-mode').hidden=['identity','review'].includes(key);
    byId('sr-review').hidden=key!=='review';byId('sr-step-title').textContent=boot.steps[step][1];
    byId('sr-scanner').hidden=true;
    const box=byId('sr-parameters');box.replaceChildren();
    if(key==='review'){localGaps();}
    else{
      const section=node('section',null,box,'sr-card');node('h2','Angaben prüfen und erfassen',section);
      const toolbar=node('div',null,section,'sr-toolbar');
      action(toolbar,'Ausgefüllte Werte dieses Schritts bestätigen',()=>{
        if(!confirm('Alle ausgefüllten Werte dieses Schritts einschließlich Einheiten am Einstellstand geprüft?'))return;
        for(const [name,spec] of Object.entries(boot.fields))if(spec.step===key&&values[name].value.trim()&&values[name].status!=='na')values[name].status='confirmed';
        changed();render();
      });
      action(toolbar,'Leere optionale Angaben: nicht zutreffend',()=>{
        const reason=prompt('Begründung für die leeren optionalen Felder und leeren Profile dieses Schritts (z. B. kein Heißkanal / keine Zusatzfunktion):');
        if(!reason?.trim())return;
        const required=['tool_no','machine_no','article_no','material_no','cycle_target','record_date','operator',...(context.masterbatch_id?['batch_no','batch_name','batch_percent']:[])];
        for(const [name,spec] of Object.entries(boot.fields))if(spec.step===key&&!values[name].value.trim()&&!required.includes(name))Object.assign(values[name],{status:'na',reason:reason.trim()});
        for(const [name,spec] of Object.entries(boot.profiles))if(spec.step===key&&!profiles[name].rows.length)Object.assign(profiles[name],{status:'na',reason:reason.trim()});
        changed();render();
      });
      const grid=node('div',null,section,'sr-grid');
      for(const [name,spec] of Object.entries(boot.fields)){
        if(spec.step!==key)continue;
        const item=values[name];const wrap=node('div',null,grid,item.status==='confirmed'?'sr-confirmed':'sr-pending');wrap.dataset.parameter=name;
        const label=node('label',spec.label,wrap);
        let n;
        const edit=v=>{item.value=v;item.status='open';item.origin='manual';item.photo_id=null;item.evidence='Bewusste Handeingabe / Korrektur';syncStatus(item);};
        if(['notes','packaging','mold_safety','core_sequence'].includes(name)){
          n=node('textarea',null,label);n.value=item.value;n.addEventListener('input',()=>{edit(n.value);changed();});n.maxLength=4000;
        }else{n=input(label,item.value,edit,spec.kind);n.maxLength=300;}
        n.dataset.field=name;bindTarget(n,wrap,{field:name});
        if(name==='nozzle_radius')node('small','Düsenradius in mm: 40, 40,5 oder R40 / R 40 eingeben. R wird beim Speichern entfernt.',wrap,'sr-note');
        unitControl(wrap,item,spec.unit);origin(wrap,item);statusControl(wrap,item,spec.label,{field:name});
      }
      for(const [name,spec] of Object.entries(boot.profiles))if(spec.step===key)renderProfile(name,spec,box);
    }
    byId('sr-back').disabled=step===0||busy;byId('sr-next').hidden=step===boot.steps.length-1;
    byId('sr-next').textContent=editable?'Speichern und weiter →':'Weiter →';byId('sr-save').hidden=!editable;
    byId('sr-manual').disabled=!editable;byId('sr-open-scan').disabled=!editable;
    if(!editable){
      byId('sr-parameters').querySelectorAll('input,select,textarea,button').forEach(n=>n.disabled=true);
      byId('sr-identities').querySelectorAll('input,select,textarea,button').forEach(n=>n.disabled=true);
    }
    paintErrors();
  }
  function renderProfile(name,spec,parent){
    const item=profiles[name],section=node('section',null,parent,'sr-card');node('h2',spec.label,section);
    section.dataset.profile=name;
    if(name==='cylinder'){
      node('p','Standardaufbau: DH → MH 3 → MH 2 → MH 1 → Einzug. Aktivierung, Soll-/Istwerte und Toleranzen an der Maschine prüfen. Zonen können umbenannt, ergänzt, verschoben oder entfernt werden.',section,'sr-note');
      if(editable&&!item.rows.length&&boot.profile_defaults?.cylinder)action(section,'Standardzonen einfügen',()=>{
        Object.assign(item,structuredClone(boot.profile_defaults.cylinder));changed();render();
      });
    }
    section.tabIndex=-1;bindTarget(section,section,{profile:name});
    node('p','Eine Zeile je Stufe / Zone. Reihenfolge ist die tatsächliche Ausführungsreihenfolge, nicht zwingend die Anordnung auf dem Bildschirm. Aktivierung ausdrücklich prüfen.',section,'sr-note');
    origin(section,item);statusControl(section,item,spec.label,{profile:name});
    const scroll=node('div',null,section,'sr-table-wrap');const table=node('table',null,scroll,'sr-table');
    const head=node('tr',null,node('thead',null,table));['Stufe / Zone','Aktiv',...spec.columns.map(c=>c[1]),'Aktion'].forEach(label=>node('th',label,head));
    const body=node('tbody',null,table);
    item.rows.forEach((row,index)=>{
      const tr=node('tr',null,body);const td=()=>node('td',null,tr);
      tr.tabIndex=-1;
      const modified=()=>{item.status='open';item.origin='manual';item.photo_id=null;syncStatus(item);};
      const labelBox=td(),labelInput=input(labelBox,row.label,v=>{row.label=v;modified();});labelInput.className='sr-profile-label';bindTarget(labelInput,labelBox,{profile:name,row:index,column:'label'});
      bindTarget(labelInput,labelBox,{profile:name,row:index});
      const activeBox=td(),activeInput=select(activeBox,[['unknown','Bitte prüfen'],['yes','Ja'],['no','Nein / inaktiv']],row.active,v=>{row.active=v;item.status='open';syncStatus(item);});bindTarget(activeInput,activeBox,{profile:name,row:index,column:'active'});
      for(const [column,label,unit] of spec.columns){
        const cell=row.values[column]||(row.values[column]={value:'',unit});const box=td();
        const control=input(box,cell.value,v=>{cell.value=v;modified();},unit?'number':'text');
        control.setAttribute('aria-label',spec.label+' · Zeile '+(index+1)+' · '+label);
        bindTarget(control,box,{profile:name,row:index,column});unitControl(box,cell,unit,modified);
      }
      const tools=td();
      action(tools,'↑',()=>{if(index){[item.rows[index-1],item.rows[index]]=[item.rows[index],item.rows[index-1]];modified();changed();render();}}).setAttribute('aria-label','Stufe nach oben');
      action(tools,'↓',()=>{if(index<item.rows.length-1){[item.rows[index],item.rows[index+1]]=[item.rows[index+1],item.rows[index]];modified();changed();render();}}).setAttribute('aria-label','Stufe nach unten');
      action(tools,'Entfernen',()=>{if(confirm('Diese Stufe aus dem Entwurf entfernen?')){item.rows.splice(index,1);modified();changed();render();}});
    });
    action(section,'+ Stufe / Zone hinzufügen',()=>{if(item.rows.length>=32){msg('Maximal 32 Stufen je Profil.',true);return;}item.rows.push({label:String(item.rows.length+1),active:'unknown',values:Object.fromEntries(spec.columns.map(([key,label,unit])=>[key,{value:'',unit}]))});item.status='open';changed();render();});
  }
  function showGaps(gaps){
    const box=byId('sr-gaps');box.replaceChildren();
    if(!gaps.length){node('p','Alle Angaben geprüft. Abschluss ist nach erfolgreicher serverseitiger Prüfung möglich.',box,'sr-success');return;}
    node('p',`${gaps.length} offene Prüfpunkte. Ein Entwurf darf jederzeit gespeichert werden.`,box,'sr-note');
    gaps.forEach(g=>action(box,g.label,()=>{step=Math.max(0,boot.steps.findIndex(s=>s[0]===g.step));render();}));
  }
  function localGaps(){
    const gaps=[];if(!data.context_confirmed)gaps.push({step:'identity',label:'Zuordnungen bestätigen'});
    for(const [key,label] of [['machine_id','Maschine auswählen'],['article_id','Artikel auswählen'],['material_id','Rohstoff auswählen']])if(!context[key])gaps.push({step:'identity',label});
    for(const [key,spec] of Object.entries(boot.fields))if(!['confirmed','na'].includes(values[key].status))gaps.push({step:spec.step,label:spec.label});
    for(const key of ['tool_no','machine_no','article_no','material_no','cycle_target','record_date','operator',...(context.masterbatch_id?['batch_no','batch_name','batch_percent']:[])])if(values[key].status==='na')gaps.push({step:boot.fields[key].step,label:boot.fields[key].label+' ist erforderlich'});
    for(const [key,spec] of Object.entries(boot.profiles))if(!['confirmed','na'].includes(profiles[key].status))gaps.push({step:spec.step,label:spec.label});
    showGaps(gaps);
  }
  async function save(release=false){
    if(busy||!editable)return false;
    setBusy(true);
    try{
      const result=await api(boot.save_url,{version,ids:ids(),context_token:contextToken,data,release});
      version=result.version;context=result.context;
      Object.assign(values,result.data.values);Object.assign(profiles,result.data.profiles);
      dirty=false;byId('sr-state').textContent=(result.state==='released'?'Geprüft abgeschlossen':'Entwurf')+' · Stand '+version;
      issues=[];
      const scannerWasOpen=!byId('sr-scanner').hidden;render();if(scannerWasOpen)byId('sr-scanner').hidden=false;
      showGaps(result.gaps);msg('Stand '+version+' gespeichert. '+(result.gaps.length?result.gaps.length+' Prüfpunkte sind noch offen.':'Alle Angaben geprüft.'));
      if(result.state==='released'){editable=false;location.reload();}
      return true;
    }catch(error){setBusy(false);failure(error);return false;}finally{setBusy(false);}
  }
  byId('sr-back').addEventListener('click',()=>{if(step>0){step--;render();}});
  byId('sr-next').addEventListener('click',async()=>{if(!editable||await save()){step++;render();}});
  byId('sr-save').addEventListener('click',()=>save());
  byId('sr-release')?.addEventListener('click',()=>{if(confirm('Alle Angaben fachlich geprüft? Abschluss macht diese Fassung schreibgeschützt. Dies ist keine Maschinen- oder Sicherheitsfreigabe.'))save(true);});
  byId('sr-manual').addEventListener('click',()=>byId('sr-parameters').querySelector('input,textarea')?.focus());
  byId('sr-open-scan').addEventListener('click',()=>{byId('sr-scanner').hidden=false;});
  if(/NC\s*5/i.test(values.controller?.value||''))byId('sr-profile').value='nc5';
  byId('sr-provider').addEventListener('change',()=>{
    byId('sr-external-warning').hidden=byId('sr-provider').value!=='groq';
    byId('sr-external-consent').checked=false;
  });
  async function scan(event){
    const file=event.target.files[0];event.target.value='';if(!file||busy||!editable)return;
    if(file.size>10*1024*1024){msg('Foto ist größer als 10 MB.',true);return;}
    const provider=byId('sr-provider').value||'local',scanStep=boot.steps[step][0];
    if(provider==='groq'){
      if(!boot.external_vision?.enabled||!boot.external_vision?.allowed){msg('Externe Erkennung ist nicht freigeschaltet.',true);return;}
      if(!boot.external_vision.steps.includes(scanStep)){msg('Groq bitte in Spritz-, Werkzeug- oder Temperaturparametern verwenden.',true);return;}
      if(!byId('sr-external-consent').checked){msg('Bitte die Übertragung dieses Fotos an Groq zuerst bewusst bestätigen.',true);return;}
      byId('sr-external-consent').checked=false;
    }
    if(!await save())return;
    setBusy(true);msg(provider==='groq'?'Foto wird extern mit Groq ausgelesen. Angaben bleiben ungeprüfte Vorschläge.':'Foto wird lokal ausgelesen. Es werden keine Parameter ungefragt geändert.');
    try{
      const payload=new FormData();payload.append('photo',file,file.name);payload.append('version',String(version));payload.append('profile',byId('sr-profile').value);
      payload.append('provider',provider);payload.append('step',scanStep);
      if(provider==='groq')payload.append('external_consent','yes');
      const result=await api(boot.photo_url,payload,true);version=result.version;
      byId('sr-state').textContent='Entwurf · Stand '+version;
      renderScan(result);msg('Foto gespeichert. Vorschläge prüfen und einzeln übernehmen; die Handeingabe bleibt verfügbar.');
    }catch(error){setBusy(false);failure(error);}finally{setBusy(false);}
  }
  function renderScan(scan){
    const box=byId('sr-scan-result');box.replaceChildren();const image=node('img',null,box,'sr-scan-image');image.src=scan.url;image.alt='Quellfoto '+scan.photo_id;
    node('h3','Erkannte Seite: '+scan.result.page,box);
    (scan.result.notes||[]).forEach(note=>node('p',note,box,'sr-note'));
    for(const proposal of scan.result.proposals||[]){
      if(!boot.fields[proposal.field])continue;
      const card=node('div',null,box,'sr-proposal');node('strong',proposal.label+': '+proposal.value+' '+proposal.unit,card);node('p','Quelle: '+proposal.evidence,card);
      const raw=String(proposal.value).trim().replace(',','.');
      if(!/^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(raw)||!Number.isFinite(Number(raw))||(proposal.field==='dosing_position'&&Number(raw)<=0)){
        node('p','Unvollständige oder unplausible OCR-Zahl. Bitte am Foto prüfen und manuell eingeben; dieser Vorschlag wird nicht übernommen.',card,'sr-error');continue;
      }
      const apply=action(card,'Als ungeprüften Vorschlag übernehmen',()=>{
        const old=values[proposal.field];if(old.value&&!confirm('Vorhandenen Wert '+old.value+' ausdrücklich durch '+proposal.value+' ersetzen?'))return;
        Object.assign(values[proposal.field],proposal,{origin:'photo',status:'open',reason:'',photo_id:scan.photo_id});
        refreshedProposal(apply,proposal.field,false);
      });
      action(card,'Wert im Formular anzeigen',()=>showTarget(proposal.field,false));
    }
    for(const [key,profile] of Object.entries(scan.result.profiles||{})){
      if(!boot.profiles[key])continue;
      const card=node('div',null,box,'sr-proposal');node('h4',boot.profiles[key].label,card);
      profile.rows.forEach(row=>node('p',row.label+': '+Object.entries(row.values).map(([key,v])=>key+' '+v.value+' '+v.unit).join(' · '),card));
      const apply=action(card,'Profil als ungeprüften Vorschlag übernehmen',()=>{
        if(profiles[key].rows.length&&!confirm('Vorhandenes Profil vollständig durch dieses Foto-Profil ersetzen?'))return;
        Object.assign(profiles[key],structuredClone(profile),{photo_id:scan.photo_id,status:'open',origin:'photo',reason:''});
        refreshedProposal(apply,key,true);
      });
      action(card,'Profil im Formular anzeigen',()=>showTarget(key,true));
    }
    const details=node('details',null,box);node('summary','Erkannten Text zur manuellen Zuordnung ansehen',details);const raw=node('textarea',null,details);raw.value=scan.result.text;raw.readOnly=true;raw.rows=12;
  }
  function refreshedProposal(button,key,isProfile){
    changed();const scannerWasOpen=!byId('sr-scanner').hidden;
    render();if(scannerWasOpen)byId('sr-scanner').hidden=false;
    button.textContent='Übernommen – noch unbestätigt';
    msg((isProfile?'Profil':'Wert')+' im Formular aktualisiert. Bitte prüfen und den Entwurf speichern.');
  }
  function showTarget(key,isProfile){
    const spec=isProfile?boot.profiles[key]:boot.fields[key];
    step=Math.max(0,boot.steps.findIndex(s=>s[0]===spec.step));render();
    const target=byId('sr-parameters').querySelector(isProfile?`[data-profile="${key}"]`:`[data-field="${key}"]`);
    target?.scrollIntoView({behavior:'smooth',block:'center'});if(!isProfile)target?.focus();
  }
  byId('sr-camera').addEventListener('change',scan);byId('sr-file').addEventListener('change',scan);
  host.querySelectorAll('label[role=button]').forEach(label=>label.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();label.querySelector('input').click();}}));
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  renderSelectors();render();
})();
