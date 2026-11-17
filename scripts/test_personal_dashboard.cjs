const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.events={};this.dataset={};this.classList={add(){}};this.disabled=false;}
 append(...items){this.children.push(...items);}replaceChildren(){this.children=[];}setAttribute(){}focus(){}
 addEventListener(key,callback){this.events[key]=callback;}
 querySelectorAll(){return this.children.filter(el=>el.tag==='button'&&el.dataset.action);}
 getBoundingClientRect(){return {top:0,height:100};}
}
const tiles=['inventory','tool_list','booking'].map(key=>({key,title:key,group:'Test',icon:'📦'}));
const grid=new Element('grid'),status={},form=new Element('form');form.elements={layout:{value:''}};
const checks=tiles.map(tile=>({value:tile.key,checked:false,events:{},addEventListener(k,f){this.events[k]=f;}}));
tiles.forEach(tile=>form.elements['position_'+tile.key]={value:99});form.querySelectorAll=()=>checks;
const source={textContent:JSON.stringify({catalog:tiles,selected:['inventory','tool_list']})};
const ids={'dashboard-catalog-data':source,'dashboard-editor':form,'dashboard-preview':grid,'dashboard-editor-status':status};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/personal_dashboard.js'),'utf8'),{document:{getElementById(id){return ids[id];},addEventListener(_,f){f();},createElement(tag){return new Element(tag);}}});
const order=()=>JSON.parse(form.elements.layout.value);
assert.deepEqual(order(),['inventory','tool_list']);
// Mobile / keyboard move using the real click handler.
grid.children[0].children[0].children[2].events.click();assert.deepEqual(order(),['tool_list','inventory']);
checks[2].checked=true;checks[2].events.change();assert.deepEqual(order(),['tool_list','inventory','booking']);
// Desktop drag: dropping in the lower half places the tile after the target.
grid.children[0].children[0].children[0].events.dragstart({dataTransfer:{setData(){}}});
grid.children[2].events.drop({preventDefault(){},clientY:90});assert.deepEqual(order(),['inventory','booking','tool_list']);
grid.children[0].children[0].children[3].events.click();assert.deepEqual(order(),['booking','tool_list']);assert.equal(checks[0].checked,false);
form.events.submit();assert.deepEqual(order(),['booking','tool_list']);
assert(!fs.readFileSync(path.join(__dirname,'../factoryos/static/js/personal_dashboard.js'),'utf8').includes('localStorage'));
console.log('PASS: ordered editor state; mobile/keyboard buttons; add/remove and checkbox synchronization; desktop drag to last position; submitted layout; no browser-local account storage.');
