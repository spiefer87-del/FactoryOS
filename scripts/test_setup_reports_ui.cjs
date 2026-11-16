/* Logic/DOM stubs only, not mobile rendering or Android camera validation. */
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
class Element{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.listeners={};this.value='';this.checked=false;this.hidden=false;this.disabled=false;this.dataset={};}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(k,v){this[k]=v;}
 removeAttribute(k){delete this[k];}
 add(option){this.children.push(option);}
 addEventListener(type,fn){(this.listeners[type]||=[]).push(fn);}
 async fire(type){for(const fn of this.listeners[type]||[])await fn({target:this,preventDefault(){}});await new Promise(setImmediate);}
 querySelectorAll(selector){const tags=selector.split(',').map(s=>s.split('[')[0]);const out=[];function walk(n){for(const c of n.children){if(tags.includes(c.tagName))out.push(c);walk(c);}}walk(this);return out;}
 querySelector(selector){return this.querySelectorAll(selector)[0];}
 focus(){this.focused=true;}
}
function setup(editable=true){
 const ids=['sr-wizard','sr-boot','sr-csrf','sr-status','sr-state','sr-identities','sr-selectors','sr-context','sr-context-confirm','sr-steps','sr-entry-mode','sr-review','sr-step-title','sr-scanner','sr-parameters','sr-back','sr-next','sr-save','sr-manual','sr-open-scan','sr-profile','sr-camera','sr-file','sr-scan-result','sr-gaps','sr-release'];
 const nodes=Object.fromEntries(ids.map(id=>[id,new Element()]));
 nodes['sr-wizard'].append(...ids.filter(id=>id!=='sr-wizard').map(id=>nodes[id]));
 const fields=Object.fromEntries(['tool_no','machine_no','article_no','material_no','cycle_target','record_date','operator','controller'].map(key=>[key,{label:key,step:key==='cycle_target'?'injection':'identity',unit:key==='cycle_target'?'s':'',kind:key==='cycle_target'?'number':'text'}]));
 const values=Object.fromEntries(Object.keys(fields).map(key=>[key,{value:key==='cycle_target'?'42':'TEST',unit:fields[key].unit,status:'open',origin:'master',reason:''}]));
 const boot={editable,version:1,report_id:1,fields,profiles:{injection_profile:{label:'Einspritzprofil',step:'injection',columns:[['position','Position','cm³']]}},units:{'cm³':['cm³','mm']},origins:{master:'Stammdatenvorschlag',manual:'Handeingabe'},
  steps:[['identity','Identität'],['injection','Spritzen'],['review','Prüfen']],data:{values,profiles:{},context_confirmed:false},context:{tool_id:1,machine_id:1,article_id:1,material_id:1},choices:{machines:[{id:1,label:'M1'}],articles:[{id:1,label:'A1'}],materials:[{id:1,label:'R1',category:'plastic'}]},save_url:'/save',photo_url:'/scan',context_url:'/context',photo_base:'/photos/0'};
 nodes['sr-boot'].textContent=JSON.stringify(boot);nodes['sr-csrf'].value='csrf';
 const calls=[];let photoData;
 const context={document:{getElementById:id=>nodes[id],createElement:tag=>new Element(tag)},window:new Element(),location:{reload(){}},structuredClone,FormData,Option:class extends Element{constructor(label,value){super('option');this.textContent=label;this.value=value;}},confirm:()=>true,prompt:()=> 'Im Test nicht zutreffend',
  fetch:async(url,options)=>{let payload=options.body instanceof FormData?null:JSON.parse(options.body);calls.push({url,payload});let response;
   if(url==='/save')response={version:calls.length+1,data:payload.data,context:payload.ids,state:'draft',gaps:[]};
   else if(url==='/context')response={context:boot.context,values:boot.data.values,choices:boot.choices};
   else response=photoData;
   return {ok:true,headers:{get:()=> 'application/json'},json:async()=>response};
  }};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/setup_reports.js'),'utf8'),context);
 return {nodes,calls,setPhoto:v=>photoData=v};
}
function all(node){const out=[];function walk(n){out.push(n);n.children.forEach(walk);}walk(node);return out;}
(async()=>{
 const {nodes,calls,setPhoto}=setup();assert.equal(calls.length,0);assert.equal(nodes['sr-context-confirm'].checked,false);
 assert.equal(nodes['sr-steps'].children.length,3);
 await nodes['sr-steps'].children[1].fire('click');
 const field=all(nodes['sr-parameters']).find(n=>n.dataset.field==='cycle_target');
 assert.equal(field.value,'42');field.value='58,5';await field.fire('input');
 await nodes['sr-save'].fire('click');
 assert.equal(calls[0].payload.data.values.cycle_target.value,'58,5');
 assert.equal(calls[0].payload.data.values.cycle_target.origin,'manual');
 assert.equal(calls[0].payload.data.values.cycle_target.status,'open');
  const afterSaveField=all(nodes['sr-parameters']).find(n=>n.dataset.field==='cycle_target');afterSaveField.value='59';await afterSaveField.fire('input');await nodes['sr-save'].fire('click');assert.equal(calls.at(-1).payload.data.values.cycle_target.value,'59');
  afterSaveField.value='58,5';
  const freshField=all(nodes['sr-parameters']).find(n=>n.dataset.field==='cycle_target');freshField.value='58,5';await freshField.fire('input');
 await nodes['sr-open-scan'].fire('click');assert.equal(nodes['sr-scanner'].hidden,false);
 setPhoto({version:8,photo_id:5,url:'/photos/5',result:{page:'injection',notes:[],text:'TEST',profiles:{},proposals:[{field:'cycle_target',label:'Zyklus',value:'60',unit:'s',evidence:'TEST'}]}});
 nodes['sr-file'].files=[new Blob(['image'],{type:'image/jpeg'})];
 await nodes['sr-file'].fire('change');
 // Receiving an OCR proposal must not overwrite the manually saved setting.
 await nodes['sr-save'].fire('click');assert.equal(calls.at(-1).payload.data.values.cycle_target.value,'58,5');
 const apply=all(nodes['sr-scan-result']).find(n=>n.textContent==='Als ungeprüften Vorschlag übernehmen');assert.ok(apply);
 await apply.fire('click');await nodes['sr-save'].fire('click');
 assert.equal(calls.at(-1).payload.data.values.cycle_target.value,'60');
 assert.equal(calls.at(-1).payload.data.values.cycle_target.status,'open');
 assert.equal(calls.at(-1).payload.data.values.cycle_target.photo_id,5);
 const add=all(nodes['sr-parameters']).find(n=>n.textContent==='+ Stufe / Zone hinzufügen');await add.fire('click');
 await nodes['sr-save'].fire('click');assert.equal(calls.at(-1).payload.data.profiles.injection_profile.rows[0].active,'unknown');
 await nodes['sr-steps'].children[2].fire('click');assert.equal(nodes['sr-review'].hidden,false);
 console.log('PASS: wizard navigation, manual source and unconfirmed status, photo proposals never overwrite automatically, explicit apply, profile activity open, saving and review DOM logic.');
})().catch(e=>{console.error(e);process.exitCode=1;});
