const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const path = require("path");
const source = fs.readFileSync(path.join(__dirname,"../factoryos/static/js/article_columns.js"),"utf8");
const keys = ["article_no","article_name","customer","material","tools","status","sampling","actions"];
function setup(saved=null,user="1",blocked=false) {
    const memory = saved || {};
    function element(dataset={}) {
        return {dataset,checked:true,listeners:{},textContent:"",open:true,
            addEventListener(type,fn){this.listeners[type]=fn;},
            classList:{values:new Set(),toggle(name,flag){flag?this.values.add(name):this.values.delete(name);}},
        };
    }
    const inputs = keys.map(key=>element({articleColumnToggle:key}));
    const rows = Array.from({length:26},()=>keys.map(key=>element({articleColumn:key})));
    const cells = rows.flat();
    const table = element({columnUser:user}); table.querySelectorAll=()=>cells;
    const count=element(),status=element(),reset=element(),picker=element();
    let focused=false; picker.querySelector=()=>({focus(){focused=true;}});
    const elements={"articles-table":table,"article-visible-count":count,"article-view-status":status,
        "article-columns-reset":reset,"article-column-picker":picker};
    const document = {getElementById:id=>elements[id],querySelectorAll:()=>inputs,addEventListener(type,fn){fn();}};
    const localStorage={getItem(key){if(blocked)throw Error("denied");return memory[key]||null;},
        setItem(key,value){if(blocked)throw Error("denied");memory[key]=value;}};
    vm.runInNewContext(source,{document,window:{localStorage}});
    function toggle(key,visible){const input=inputs[keys.indexOf(key)];input.checked=visible;input.listeners.change();}
    return {memory,rows,cells,inputs,count,status,reset,picker,toggle,isFocused:()=>focused};
}
const first=setup();
assert.strictEqual(first.count.textContent,"8/8");
first.toggle("sampling",false);
assert.strictEqual(first.count.textContent,"7/8");
first.rows.forEach(row=>{
    assert.strictEqual(row.length,8); // Stable cell indices for sorting/pagination.
    assert(row[6].classList.values.has("article-column-hidden"));
    assert(!row[0].classList.values.has("article-column-hidden"));
});
const restored=setup(first.memory);
assert.strictEqual(restored.inputs[6].checked,false);
assert.strictEqual(setup(first.memory,"2").inputs[6].checked,true);
keys.forEach(key=>restored.toggle(key,false));
assert.strictEqual(restored.count.textContent,"1/8");
restored.reset.listeners.click();
assert.strictEqual(restored.count.textContent,"8/8");
assert.strictEqual(setup(restored.memory).count.textContent,"8/8");
const blocked=setup(null,"1",true);
blocked.toggle("sampling",false);
assert.strictEqual(blocked.count.textContent,"7/8");
assert(blocked.status.textContent.includes("nicht verfügbar"));
const corrupt=setup({"factoryos.articles.columns.v1.user.1":"NOT JSON"});
assert.strictEqual(corrupt.count.textContent,"8/8");
const invalid=setup({"factoryos.articles.columns.v1.user.1":JSON.stringify({article_no:false,sampling:false,customer:"false",unknown:false})});
assert.strictEqual(invalid.inputs[0].checked,true);
assert.strictEqual(invalid.inputs[2].checked,true);
assert.strictEqual(invalid.inputs[6].checked,false);
invalid.picker.listeners.keydown({key:"Escape"});
assert.strictEqual(invalid.picker.open,false);assert(invalid.isFocused());
console.log("PASS: defaults, header/all rows toggled without removing cells, persistence, per-user isolation, required article number, reset, storage failure/corruption/invalid data, Escape/focus.");
