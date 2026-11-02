"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const path = require("path");
const script = fs.readFileSync(path.join(__dirname, "../factoryos/static/js/article_table_scroll.js"), "utf8");
function fixture(withResizeObserver) {
    const events = {}, pickerEvents = {};
    const region = { scrollWidth: 1600, clientWidth: 330 };
    const table = {}, hint = { hidden: true }, observed = [];
    const picker = {addEventListener: (name, fn) => pickerEvents[name] = fn};
    const context = {
        document: {
            addEventListener: (name, fn) => events[name] = fn,
            querySelector: () => region,
            getElementById: id => ({"articles-table":table, "article-table-scroll-hint":hint, "article-column-picker":picker})[id]
        },
        window: {addEventListener:(name, fn) => events[name]=fn, requestAnimationFrame:fn=>fn()}
    };
    if (withResizeObserver) context.ResizeObserver = class {
        constructor(callback) { events.resizeObserver=callback; }
        observe(element) { observed.push(element); }
    };
    vm.runInNewContext(script, context);
    events.DOMContentLoaded();
    assert.strictEqual(hint.hidden, false);
    if (withResizeObserver) assert.deepStrictEqual(observed, [region, table]);
    region.scrollWidth = 330;
    pickerEvents.change();
    assert.strictEqual(hint.hidden, true);
    region.scrollWidth = 900;
    events.resize();
    assert.strictEqual(hint.hidden, false);
    region.clientWidth = 1000;
    pickerEvents.click();
    assert.strictEqual(hint.hidden, true);
}
fixture(true);
fixture(false);
vm.runInNewContext(script, {
    document: {addEventListener:(name, callback)=>callback(), querySelector:()=>null, getElementById:()=>null}
});
console.log("PASS: scroll hint follows overflow, column changes, resizing, ResizeObserver/fallback and missing table.");
