const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Option {
 constructor(textContent,value,defaultSelected=false,selected=false){Object.assign(this,{textContent,value,selected});}
 cloneNode(){return new Option(this.textContent,this.value);}
}
class Select {
 constructor(options=[]){this.options=options;this.value='';this.events={};}
 replaceChildren(...options){this.options=options;this.value=options[0]?.value||'';}
 add(option){this.options.push(option);if(option.selected)this.value=option.value;}
 addEventListener(name,cb){this.events[name]=cb;}
}
const search={value:'',events:{},addEventListener(n,cb){this.events[n]=cb;}},select=new Select([new Option('Bitte auswählen',''),new Option('A1 Deckel','1'),new Option('A2 Gehäuse','2'),new Option('A3 Kappe','3')]),tool=new Select(),status={};
const nodes={'defect-article-search':search,'defect-article':select,'defect-tool':tool,'defect-article-status':status,'defect-article-tools':{textContent:JSON.stringify({'1':[{number:'COR001',external:'EXT77'}],'2':[{number:'COR001',external:''}],'3':[{number:'OTHER',external:''}]})}};
vm.runInNewContext(fs.readFileSync('factoryos/static/js/article_defects.js','utf8'),{Option,document:{getElementById:id=>nodes[id],addEventListener:(n,cb)=>cb()}});
const find=q=>{search.value=q;search.events.input();};
find('other');assert.equal(select.value,'3');assert.equal(tool.value,'OTHER');
find('cor001');assert.equal(select.value,'');assert.equal(select.options.length,3);assert.equal(tool.value,'');
select.value='2';select.events.change();assert.equal(tool.options[1].value,'COR001');assert.equal(tool.value,'');
find('ext77');assert.equal(select.value,'1');assert.equal(tool.value,'COR001');
find('Kappe');assert.equal(select.value,'3');assert.equal(tool.value,'');
find('not found');assert.equal(select.value,'');assert.equal(tool.options.length,1);
find('');assert.equal(select.options.length,4);
console.log('PASS: article/internal/external tool search, single result, ambiguous articles require selection, optional tool resets, no match and clear');
