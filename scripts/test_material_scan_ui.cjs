/* Logic-only DOM stubs: not an Android/browser rendering test. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.value='';this.checked=false;this.hidden=false;this.disabled=false;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  add(option){this.children.push(option);}
  addEventListener(event,handler){this.listeners[event]=handler;}
  setAttribute(){}
  querySelectorAll(){return [];}
  querySelector(tag){return this.children.find(child=>child.tag===tag);}
  dispatchEvent(event){this.listeners[event.type]?.(event);}
  scrollIntoView(){}
}
const ids=['material-scanner','material-create-form','material-scan-status','material-scan-review','material-scan-choices','material-scan-csrf','material-scan-text','material-scan-readability','material-scan-notes','material-scan-duplicates','material-scan-fields','material-scan-missing','material-scan-metadata','material-scan-apply','material-scan-camera','material-scan-file','material-scan-again','material-scan-parse'];
const nodes=Object.fromEntries(ids.map(id=>[id,new Element()]));
nodes['material-scanner'].dataset={scanUrl:'/scan',textUrl:'/scan/text'};
nodes['material-scan-choices'].textContent=JSON.stringify({material_type:{plastic:'Kunststoff',masterbatch:'Masterbatch'},polymer_type:{ABS:'ABS',PA6:'PA6'}});
for(const id of ['material-scan-missing','material-scan-metadata'])nodes[id].append(new Element('div'));
const fields={name:new Element('input'),manufacturer:new Element('input'),color_no:new Element('input'),material_type:new Element('select'),polymer_type:new Element('select')};
nodes['material-create-form'].elements={namedItem:name=>fields[name]};
let responseData;
const context={document:{getElementById:id=>nodes[id],createElement:tag=>new Element(tag)},window:new Element(),location:{origin:'https://example.invalid'},URL,FormData,Event,
  Option:class {constructor(label,value){this.label=label;this.value=value;}},confirm:()=>true,
  fetch:async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>responseData})};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/material_scan.js'),'utf8'),context);
async function render(data){responseData=data;nodes['material-scan-parse'].listeners.click();await new Promise(setImmediate);}
function row(label){return nodes['material-scan-fields'].children.find(row=>row.children[0]?.children[1]?.textContent===label);}
(async()=>{
  await render({text:'test',proposals:[{field:'name',label:'Bezeichnung',value:'TEST G123',certainty:'review',evidence:'Product'},
    {field:'color_no',label:'Farbnummer',value:'000000',certainty:'label',evidence:'Color'},
    {field:'material_no',label:'Nicht erlaubt',value:'HIDDEN',certainty:'label'}],
    missing_fields:[{field:'manufacturer',label:'Hersteller',reason:'Nicht erkannt'},
      {field:'material_type',label:'Materialart',reason:'Nicht erkannt'},
      {field:'polymer_type',label:'Kunststoffart',reason:'Nicht erkannt'}],
    label_metadata:[{label:'Partie / Los',value:'000202882-1'}]});
  assert.equal(nodes['material-scan-fields'].children[0],row('Hersteller'));
  assert.equal(row('Hersteller').children[1].value,'');
  assert.equal(row('Hersteller').children[0].children[0].checked,false);
  assert.equal(row('Materialart').children[1].value,'');
  assert.equal(row('Materialart').children[1].children[0].value,'');
  assert.equal(row('Bezeichnung').children[0].children[0].checked,false);
  assert.equal(row('Nicht erlaubt'),undefined);
  assert.equal(fields.name.value,''); // Never apply automatically.
  assert.equal(nodes['material-scan-metadata'].hidden,false);
  assert.match(nodes['material-scan-metadata'].querySelector('div').children[0].textContent,/000202882-1/);
  row('Hersteller').children[1].value='Example Company';
  row('Hersteller').children[0].children[0].checked=true;
  row('Bezeichnung').children[0].children[0].checked=true;
  nodes['material-scan-apply'].listeners.click();
  assert.equal(fields.manufacturer.value,'Example Company');
  assert.equal(fields.name.value,'TEST G123');
  assert.equal(fields.color_no.value,'000000');
  assert.equal(fields.material_type.value,'');
  assert.equal(fields.polymer_type.value,'');
  console.log('PASS: manufacturer first, missing fields blank/unchecked, uncertain proposals unchecked, leading zeros, allowlist, metadata read-only, explicit field transfer.');
})().catch(error=>{console.error(error);process.exitCode=1;});
