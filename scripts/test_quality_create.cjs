const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
class Option{constructor(text,value){this.textContent=text;this.value=String(value);}cloneNode(){return new Option(this.textContent,this.value);}}
function select(options=[]){return {options,value:'',events:{},addEventListener(k,f){this.events[k]=f;},replaceChildren(...rows){this.options=rows;this.value='';},add(row){this.options.push(row);}};}
const article=select([new Option('Bitte wählen',''),...Array.from({length:500},(_,i)=>new Option(i===0?'AB001 - Deckel':i===1?'AB002 - Abdeckung':`XZ${i} - Teil ${i}`,i+1))]);
const tool=select(),search={value:'',events:{},addEventListener(k,f){this.events[k]=f;}},status={textContent:''},toolStatus={textContent:''};
article.form={events:{},addEventListener(k,f){this.events[k]=f;}};
const ids={'article-select':article,'article-search':search,'tool-select':tool,'article-search-status':status,'tool-selection-status':toolStatus};
let pending=[];
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../factoryos/static/js/quality_create.js'),'utf8'),{Option,document:{addEventListener(_,f){f();},getElementById(id){return ids[id];}},fetch(url){return new Promise(resolve=>pending.push({url,resolve}));}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 search.value='a';search.events.input();assert.equal(article.options.length,501);
 search.value='ab';search.events.input();assert.equal(article.options.length,3);
 search.value='deckel';search.events.input();assert.equal(article.options.length,2);
 article.value='1';article.events.change();assert(pending[0].url.endsWith('/1'));
 search.value='ab';search.events.input();article.value='2';article.events.change();
 pending[1].resolve({ok:true,json:async()=>[{id:20,text:'COR20'}]});await tick();assert.equal(tool.options[1].value,'20');
 pending[0].resolve({ok:true,json:async()=>[{id:10,text:'COR10'}]});await tick();assert.equal(tool.options[1].value,'20');
 search.value='kein treffer';search.events.input();assert.equal(article.value,'');assert(tool.disabled);assert.match(status.textContent,/Keine passenden/);
 search.value='';search.events.input();assert.equal(article.options.length,501);
 let blocked=false;article.form.events.submit({preventDefault(){blocked=true;}});assert(blocked);
 console.log('PASS: 500 articles; two-character threshold; number/name case-insensitive filtering; clearing restores all; invalidated selection clears tool; stale tool responses ignored; incomplete submit blocked.');
})();
