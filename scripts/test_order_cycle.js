"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert"),path=require("path");
const code=fs.readFileSync(path.join(__dirname,"../factoryos/static/js/order_cycle.js"),"utf8");
function setup(saved="") {
    const event={};
    const fields={
        "order-article":{value:"",addEventListener:(type,fn)=>event.article=fn},
        "cycle_time_s":{value:saved,addEventListener:(type,fn)=>event.cycle=fn},
        "order-cycle-hint":{textContent:""},
        "order-articles":{options:[
            {value:"A1",dataset:{cycle:"12.5"}},
            {value:"A2",dataset:{cycle:"30"}},
            {value:"BAD",dataset:{cycle:"Infinity"}}
        ]}
    };
    vm.runInNewContext(code,{document:{getElementById:id=>fields[id],addEventListener:(type,fn)=>fn()},Number});
    return {fields,event};
}
const {fields:f,event:e}=setup();
f["order-article"].value="A1";e.article();
assert.strictEqual(f.cycle_time_s.value,"12.5");
f["order-article"].value="A2";e.article();
assert.strictEqual(f.cycle_time_s.value,"30");
f.cycle_time_s.value="21";e.cycle();
f["order-article"].value="A1";e.article();
assert.strictEqual(f.cycle_time_s.value,"21");
const saved=setup("45");
saved.fields["order-article"].value="A1";saved.event.article();
assert.strictEqual(saved.fields.cycle_time_s.value,"45");
const invalid=setup();
invalid.fields["order-article"].value="BAD";invalid.event.article();
assert.strictEqual(invalid.fields.cycle_time_s.value,"");
assert(invalid.fields["order-cycle-hint"].textContent.includes("Kein gültiger"));
console.log("PASS: article-cycle proposals, article changes, preserved manual/saved values and invalid reference handling.");
