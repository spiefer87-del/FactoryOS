/* The reason shortcut navigates immediately; ordinary reasons keep the existing form. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
let change,assigned=[];
const reasons={selectedOptions:[{dataset:{}}],addEventListener(name,fn){assert.equal(name,'change');change=fn;}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/deviation_actions.js'),'utf8'),{
  document:{getElementById:id=>id==='deviation-reason'?reasons:null},URL,
  location:{origin:'https://factoryos.test',assign:url=>assigned.push(url)}
});
change();assert.deepEqual(assigned,[]);
reasons.selectedOptions[0].dataset.orderEditUrl='/orders/edit/8?focus=quantity#order-quantity-section';
change();assert.deepEqual(assigned,['https://factoryos.test/orders/edit/8?focus=quantity#order-quantity-section']);
reasons.selectedOptions[0].dataset.orderEditUrl='https://foreign.test/';change();assert.equal(assigned.length,1);
reasons.selectedOptions[0].dataset={};change();assert.equal(assigned.length,1);
console.log('PASS: reason selection opens the quantity editor immediately, normal reasons preserve their form and foreign targets are rejected.');
