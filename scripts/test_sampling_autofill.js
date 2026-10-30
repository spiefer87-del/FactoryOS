// DOM-level event tests without an external browser or network.
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const path = require("path");
const sourceCode = fs.readFileSync(path.join(__dirname, "../factoryos/static/js/sampling_autofill.js"), "utf8");

function setup(saved = false, tomselect = false, recipe = false) {
    const ids = ["article_id", "material_id", "tool_id", "customer_id", "reason", "color",
        "material_confirmed", "sampling-material-warning", "group-material_id",
        "sampling-reference-values", "sampling-autofill-message", "sampling-stock-material", "sampling-autofill-data",
        "masterbatch_id", "masterbatch_percent", "ral_color", "color_confirmed", "sampling-color-warning",
        "group-masterbatch_id", "group-masterbatch_percent", "group-ral_color", "group-color"];
    const fields = Object.fromEntries(ids.map(id => [id, {
        value:"", hidden:false, required:false, checked:false, textContent:"", children:[],
        listeners:{}, addEventListener(type, fn){(this.listeners[type] ||= []).push(fn);},
        dispatch(type){(this.listeners[type] || []).forEach(fn => fn());},
        append(...children){this.children.push(...children);},
        replaceChildren(){this.children=[];},
        classList:{values:new Set(), toggle(name, value){value ? this.values.add(name) : this.values.delete(name);}},
        options:[]
    }]));
    fields.material_id.options = [{value:"10",textContent:"R10 ABS"}, {value:"20",textContent:"R20 PP"}];
    fields.reason.value="repair";
    if (saved) {
        fields.article_id.value="1"; fields.customer_id.value="99";
        fields.tool_id.value="99"; fields.material_id.value="20"; fields.color.value="Manuelle Sonderfarbe";
        fields.material_confirmed.checked=true;
    }
    if (tomselect) {
        ["customer_id","tool_id","material_id"].forEach(id => {
            fields[id].tomselect={setValue(value,silent){assert.strictEqual(silent,true);fields[id].value=value;}};
        });
    }
    fields["sampling-autofill-data"].textContent=JSON.stringify({
        catalog:{
            articles:{
                "1":{customer_id:"1",material_id:"10",tool_id:"1",tool_count:1,tool_names:["W1"],reference:{Artikel:"A1"},
                    ...(recipe?{masterbatch_id:"30",masterbatch_percent:2.5}:{})},
                "2":{customer_id:"2",material_id:"20",tool_id:"",tool_count:2,tool_names:["W2","W3"],reference:{Artikel:"A2"}},
                "3":{customer_id:"",material_id:"",tool_id:"",tool_count:0,tool_names:[],reference:{Artikel:"A3"}}
            },
            materials:{"10":{color:"Natur",reference:{Material:"ABS"}},"20":{color:"Rot",reference:{Material:"PP"}},
                "30":{color:"Lichtgrau",ral_color:"RAL 7035"},"40":{color:"Schwarz",ral_color:"RAL 9005"}},
            tools:{"1":{reference:{Kavitäten:2}}}
        },
        ids:{article_id:"1",tool_id:"99",material_id:"20"}, saved:saved?{Artikel:"Gespeicherter Stand"}:null
    });
    const document = {
        getElementById:id=>fields[id],
        createElement:()=>({textContent:"",children:[],append(...children){this.children.push(...children);}}),
        addEventListener:(type,fn)=>fn()
    };
    vm.runInNewContext(sourceCode,{document,console});
    function change(id,value){fields[id].value=value;fields[id].dispatch("change");}
    return {fields,change};
}
for (const ts of [false,true]) {
    const {fields:f,change}=setup(false,ts);
    change("article_id","1");
    assert.strictEqual(f.customer_id.value,"1");
    assert.strictEqual(f.tool_id.value,"1");
    assert.strictEqual(f.material_id.value,"10");
    assert.strictEqual(f.color.value,"Natur");
    change("article_id","2");
    assert.strictEqual(f.customer_id.value,"2");
    assert.strictEqual(f.tool_id.value,"");
    assert(f["sampling-autofill-message"].textContent.includes("Mehrere Werkzeuge"));
    change("customer_id","MANUAL");
    change("article_id","1");
    assert.strictEqual(f.customer_id.value,"MANUAL");
    change("reason","material_change");
    assert.strictEqual(f["sampling-material-warning"].hidden,false);
    assert.strictEqual(f.material_confirmed.required,true);
    assert(f["group-material_id"].classList.values.has("sampling-material-attention"));
    f.material_confirmed.checked=true;
    change("material_id","20");
    assert.strictEqual(f.material_confirmed.checked,false);
    assert.strictEqual(f.color.value,"Rot");
    change("reason","color_change");
    assert.strictEqual(f.color.value,"");
    change("article_id","3");
    assert.strictEqual(f.tool_id.value,"");
    assert.strictEqual(f.material_id.value,"20"); // manual value preserved
    change("article_id","");
    assert.strictEqual(f.customer_id.value,"MANUAL");
}
const {fields:s,change}=setup(true,true);
assert.strictEqual(s.customer_id.value,"99");
assert.strictEqual(s.color.value,"Manuelle Sonderfarbe");
assert.strictEqual(s.material_confirmed.checked,true);
change("article_id","2");
assert.strictEqual(s.customer_id.value,"99");
assert.strictEqual(s.color.value,"Manuelle Sonderfarbe");
assert.strictEqual(s.material_confirmed.checked,false);
console.log("PASS: native and TomSelect events, defaults, multiple tools, article changes, clearing, manual/saved values, yellow material warning, confirmation reset, color change.");
for (const ts of [false,true]) {
    const {fields:f,change:c}=setup(false,ts,true);
    c("article_id","1");
    assert.strictEqual(f.masterbatch_id.value,"30");
    assert.strictEqual(f.masterbatch_percent.value,"2.5");
    assert.strictEqual(f.color.value,"Lichtgrau");
    assert.strictEqual(f.ral_color.value,"RAL 7035");
    c("masterbatch_id","40");
    assert.strictEqual(f.color.value,"Schwarz");
    assert.strictEqual(f.masterbatch_percent.value,""); // Different batch: no invented dosage.
    c("masterbatch_percent","3");
    c("article_id","2");
    assert.strictEqual(f.masterbatch_percent.value,"3"); // manual preserved
    c("reason","color_change");
    assert.strictEqual(f["sampling-color-warning"].hidden,false);
    assert(f["group-masterbatch_id"].classList.values.has("sampling-material-attention"));
    c("masterbatch_id","30");
    assert.strictEqual(f.ral_color.value,"RAL 7035");
    assert.strictEqual(f.color_confirmed.required,true);
    f.color_confirmed.checked=true;
    c("ral_color","RAL 9010");
    assert.strictEqual(f.color_confirmed.checked,false);
    f.color_confirmed.checked=true;
    c("masterbatch_percent","4");
    assert.strictEqual(f.color_confirmed.checked,false);
}
console.log("PASS: article masterbatch/color/RAL/dosage suggestions, manual preservation, no dosage copied across different batches, yellow color warning and confirmation reset.");

