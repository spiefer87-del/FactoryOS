const fs=require("fs"),vm=require("vm"),path=require("path"),assert=require("assert");
const source=name=>fs.readFileSync(path.join(__dirname,"../factoryos/static/js",name),"utf8");
const clone=v=>JSON.parse(JSON.stringify(v));
const keys=["article_no","article_name","customer","material","tools","status","sampling","actions"];
async function main(){
    // Exercise the real shared client: serialized saves, version conflicts and errors.
    const initial=Object.fromEntries(keys.map(k=>[k,true]));
    const server={values:{...initial},version:0};let conflict=true,fail=false;const calls=[];
    const boot={user_id:7,csrf:"TOKEN",url:"/profile/preferences/SECTION",sections:{"articles.columns":clone(server)}};
    const window={fetch:async(url,options)=>{
        assert.strictEqual(options.credentials,"same-origin");assert.strictEqual(options.headers["X-FactoryOS-User"],"7");assert.strictEqual(options.headers["X-CSRF-Token"],"TOKEN");
        assert.strictEqual(url,"/profile/preferences/articles.columns");
        const payload=JSON.parse(options.body);calls.push(payload);
        if(fail)throw Error("offline");
        if(conflict){conflict=false;server.values.material=false;server.version=1;return {status:409,ok:false,json:async()=>({current:clone(server)})};}
        assert.strictEqual(payload.version,server.version);
        Object.assign(server.values,payload.values);server.version++;
        return {status:200,ok:true,json:async()=>clone(server)};
    }};
    vm.runInNewContext(source("user_preferences.js"),{window,document:{getElementById:()=>({textContent:JSON.stringify(boot)})},Map,Promise,JSON,encodeURIComponent,Error});
    const client=window.FactoryOSPreferences;
    assert(!client.has("articles.columns"));
    await client.save("articles.columns",{sampling:false});
    assert.strictEqual(server.values.material,false);assert.strictEqual(server.values.sampling,false);
    await Promise.all([client.save("articles.columns",{sampling:true}),client.save("articles.columns",{customer:false})]);
    assert(client.has("articles.columns"));assert.strictEqual(client.get("articles.columns").customer,false);
    const copy=client.get("articles.columns");copy.customer=true;assert.strictEqual(client.get("articles.columns").customer,false);
    fail=true;await assert.rejects(client.save("articles.columns",{tools:false}),/offline/);
    fail=false;await client.save("articles.columns",{tools:false});assert.strictEqual(server.values.tools,false);

    function el(dataset={}){return {dataset,checked:true,disabled:false,hidden:true,open:true,textContent:"",style:{},listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},classList:{values:new Set(),toggle(name,on){on?this.values.add(name):this.values.delete(name);}}};}
    function articleSetup({saved=true,legacy=null,broken=false}={}){
        const values={...initial,sampling:false};const patches=[];
        const inputs=keys.map(k=>el({articleColumnToggle:k}));
        const rows=Array.from({length:26},()=>keys.map(k=>el({articleColumn:k})));
        const elements={"articles-table":{querySelectorAll:()=>rows.flat()},"article-visible-count":el(),"article-view-status":el(),"article-columns-reset":el(),"article-column-picker":el()};
        let focused=false;elements["article-column-picker"].querySelector=()=>({focus(){focused=true;}});
        const prefs={userId:7,get:()=>({...values}),has:()=>saved,save:(section,patch)=>{assert.strictEqual(section,"articles.columns");patches.push(clone(patch));if(broken)return Promise.reject(Error("offline"));Object.assign(values,patch);return Promise.resolve({...values});}};
        const window={FactoryOSPreferences:prefs,localStorage:{getItem(key){assert.strictEqual(key,"factoryos.articles.columns.v1.user.7");return JSON.stringify(legacy);}}};
        const document={getElementById:id=>elements[id],querySelectorAll:()=>inputs,addEventListener(type,fn){fn();}};
        vm.runInNewContext(source("article_columns.js"),{window,document});
        return {elements,inputs,rows,patches,prefs,focused:()=>focused,toggle(key,on){const input=inputs[keys.indexOf(key)];input.checked=on;input.listeners.change();}};
    }
    const a=articleSetup();assert.strictEqual(a.elements["article-visible-count"].textContent,"7/8");
    a.rows.forEach(row=>{assert.strictEqual(row.length,8);assert(row[6].classList.values.has("article-column-hidden"));});
    a.toggle("customer",false);await Promise.resolve();assert.strictEqual(a.patches[0].customer,false);
    a.elements["article-columns-reset"].listeners.click();await Promise.resolve();assert.strictEqual(a.elements["article-visible-count"].textContent,"8/8");
    a.elements["article-column-picker"].listeners.keydown({key:"Escape"});assert(a.focused());
    const legacy=articleSetup({saved:false,legacy:{sampling:false,customer:false,article_no:false}});await Promise.resolve();assert.strictEqual(legacy.patches[0].customer,false);assert(!("article_no" in legacy.patches[0]));
    const existing=articleSetup({saved:true,legacy:{sampling:true}});assert.strictEqual(existing.patches.length,0);
    const failed=articleSetup({broken:true});failed.toggle("sampling",true);await Promise.resolve();await Promise.resolve();assert(failed.elements["article-view-status"].textContent.includes("Nicht gespeichert"));
    failed.prefs.save=(section,patch)=>{failed.patches.push(clone(patch));return Promise.resolve(patch);};failed.toggle("customer",false);await Promise.resolve();assert.strictEqual(failed.patches.at(-1).sampling,true); // failed changes retried with next save

    // Legacy tools were shared browser-wide: require explicit confirmation to import.
    function toolsSetup(saved=false){
        const values={tool_no:true,location:true,name:true,actions:true};const patches=[];let confirm=true;
        const toggles=[el({defaultVisible:"true"}),el({defaultVisible:"true"}),el({defaultVisible:"true"})];toggles.forEach((t,i)=>{t.value=["tool_no","location","name"][i];});
        const cells=Object.keys(values).map(k=>el({col:k}));const elements={"tools-table":{querySelectorAll:()=>cells},"tool-view-status":el(),"resetToolColumns":el(),"importLegacyToolColumns":el()};
        const prefs={get:()=>({...values}),has:()=>saved,save:(section,patch)=>{patches.push(clone(patch));Object.assign(values,patch);return Promise.resolve(values);}};
        const window={FactoryOSPreferences:prefs,confirm:()=>confirm,localStorage:{getItem:()=>JSON.stringify(["tool_no"])}},document={getElementById:id=>elements[id],querySelectorAll:()=>toggles,addEventListener(type,fn){fn();}};
        vm.runInNewContext(source("tool_columns.js"),{window,document});return {elements,patches,toggles,cells,setConfirm(v){confirm=v;}};
    }
    const tools=toolsSetup();assert.strictEqual(tools.patches.length,0);assert.strictEqual(tools.elements.importLegacyToolColumns.hidden,false);
    tools.setConfirm(false);tools.elements.importLegacyToolColumns.listeners.click();assert.strictEqual(tools.patches.length,0);
    tools.setConfirm(true);tools.elements.importLegacyToolColumns.listeners.click();await Promise.resolve();assert.strictEqual(tools.patches[0].location,false);assert.strictEqual(tools.patches[0].actions,true);assert.strictEqual(tools.elements.importLegacyToolColumns.hidden,true);
    tools.elements.resetToolColumns.listeners.click();await Promise.resolve();assert.strictEqual(tools.patches.at(-1).location,true);
    assert.strictEqual(toolsSetup(true).elements.importLegacyToolColumns.hidden,true);
    console.log("PASS: serialized account saves, conflict merge/retry, offline/recovery, headers, article server defaults/migration/reset/stable cells/failure reporting, tool explicit legacy import, reset and mandatory identity.");
}
main().catch(error=>{console.error(error);process.exitCode=1;});
