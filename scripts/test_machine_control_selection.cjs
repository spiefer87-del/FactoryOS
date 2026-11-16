/* DOM/logic regression only, not a real Android/browser rendering test. */
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
class Element{
 constructor(){this.value='';this.checked=false;this.hidden=false;this.listeners={};this.textContent='';}
 addEventListener(name,fn){(this.listeners[name]||=[]).push(fn);}
 removeAttribute(name){delete this[name];}
 focus(){this.focused=true;}
 fire(name,extra={}){const event={defaultPrevented:false,preventDefault(){this.defaultPrevented=true;},...extra};for(const fn of this.listeners[name]||[])fn(event);return event;}
}
const ids=['control-selection-data','control-command-form','control-order','control-tool','control-tool-confirmed','control-tool-confirmation-no','control-tool-confirm-label','control-selection-error','control-proposal','control-sampling-note','control-sampling-prepare','control-use-stock'];
const n=Object.fromEntries(ids.map(id=>[id,new Element()]));
n['control-selection-data'].textContent=JSON.stringify({tools:[{number:'A',name:'Werkzeug A'},{number:'B',name:'Werkzeug B'}],
 stock:{number:'A',name:'Werkzeug A',source:'Zuletzt montiert'},orders:{
  '1':{sampling:false,ready:true,note:'Fertigungsauftrag',proposal:{number:'A',name:'Werkzeug A',source:'Auftrag'}},
  '2':{sampling:true,ready:false,note:'Musterung · Für andere Maschine vorgesehen – Wechsel bestätigen',prepare_url:'/prepare',proposal:{number:'B',name:'Werkzeug B',source:'Musterungsstamm'}}}});
n['control-order'].value='1';n['control-tool'].value='A';n['control-tool-confirmed'].checked=true;
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/machine_control_selection.js'),'utf8'),{document:{getElementById:id=>n[id]}});
const tool=n['control-tool'],check=n['control-tool-confirmed'],token=n['control-tool-confirmation-no'],form=n['control-command-form'];
const submit=action=>form.fire('submit',{submitter:{value:action}});
assert.equal(tool.value,'A');assert.equal(check.checked,false);assert.equal(token.value,'');
assert.equal(submit('start').defaultPrevented,true);
check.checked=true;check.fire('change');assert.equal(token.value,'A');assert.equal(submit('start').defaultPrevented,false);
tool.value='B';tool.fire('input');assert.equal(check.checked,false);assert.equal(token.value,'');assert.equal(submit('setup').defaultPrevented,true);
n['control-order'].value='2';n['control-order'].fire('change');
assert.equal(tool.value,'B');assert.equal(check.checked,false);assert.equal(n['control-sampling-prepare'].hidden,false);
assert.equal(n['control-sampling-prepare'].href,'/prepare');assert.ok(n['control-sampling-note'].textContent.includes('andere Maschine'));
check.checked=true;check.fire('change');assert.equal(submit('start').defaultPrevented,true,'Foreign/draft sampling cannot start just by acknowledging a tool');
assert.equal(n['control-use-stock'].fire('click').defaultPrevented,true);
assert.equal(tool.value,'A');assert.equal(check.checked,false);assert.equal(token.value,'');
check.checked=true;check.fire('change');assert.equal(submit('unsetup').defaultPrevented,false,'Teardown ignores an unrelated selected sampling');
n['control-order'].value='';n['control-order'].fire('change');assert.equal(n['control-sampling-prepare'].hidden,true);
tool.value='B';tool.fire('input');check.checked=true;check.fire('change');assert.equal(submit('setup').defaultPrevented,false,'Manual master tool without order is allowed');
tool.value='UNKNOWN';tool.fire('input');check.checked=true;check.fire('change');assert.equal(submit('setup').defaultPrevented,true);
assert.ok(n['control-selection-error'].textContent.includes('Werkzeugstamm'));
assert.equal(submit('maintenance').defaultPrevented,false,'No irrelevant tool requirement for maintenance');
assert.equal(submit('preview_selection').defaultPrevented,false,'Preview is navigation only');
console.log('PASS: concrete tool proposals, checkbox and matching-number token, reset on edits/order change/stock choice, foreign sampling guard, master-only manual/no-order choices and action-specific validation.');
