const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const path = require("path");
const source = fs.readFileSync(path.join(__dirname,"../factoryos/static/js/article_sampling_history.js"),"utf8");
for (const mode of ["open", "blocked", "error", "modified"]) {
    let click, opened = false, prevented = false;
    const popup = {opener:{}};
    const link = {href:"https://example.invalid/masterdata/articles/1/history",addEventListener(type,fn){click=fn;}};
    const document = {addEventListener(type,fn){fn();},querySelectorAll(){return [link];}};
    const window = {open(url,target,features){opened=true;assert.strictEqual(url,link.href);assert(features.includes("popup=yes"));if(mode==="error")throw Error("blocked");return mode==="blocked"?null:popup;}};
    vm.runInNewContext(source,{document,window});
    click({button:0,ctrlKey:mode==="modified",preventDefault(){prevented=true;}});
    assert.strictEqual(opened,mode!=="modified");
    assert.strictEqual(prevented,mode==="open");
    if(mode==="open")assert.strictEqual(popup.opener,null);
}
console.log("PASS: popup, opener isolation, blocked/error fallback, modified-click behavior.");
