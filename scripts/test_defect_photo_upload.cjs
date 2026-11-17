const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Node {
 constructor(){this.events={};this.children=[];this.value='';}
 addEventListener(n,cb){this.events[n]=cb;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
}
const form=new Node(),status=new Node(),previews=new Node(),submit=new Node(),camera=new Node(),gallery=new Node();
form.dataset={savedPhotos:'0'};form.action='/create';form.querySelector=()=>submit;form.querySelectorAll=()=>[camera,gallery];form.reportValidity=()=>true;
let request=null,requests=0,navigated=false,revoked=0;
const nodes={'defect-editor':form,'defect-photo-status':status,'defect-photo-previews':previews};
class TestImage{constructor(){this.naturalWidth=6000;this.naturalHeight=4500;}set src(v){if(v)queueMicrotask(()=>this.onload());}}
class TestFormData{constructor(){this.files=[];}delete(){}append(name,blob,filename){this.files.push({name,blob,filename});}}
vm.runInNewContext(fs.readFileSync('factoryos/static/js/defect_photo_upload.js','utf8'),{
 document:{getElementById:id=>nodes[id],addEventListener:(n,cb)=>cb(),createElement:tag=>{
  const node=new Node();if(tag==='canvas'){node.getContext=()=>({fillRect(){},drawImage(){}});node.toBlob=cb=>cb({size:Math.ceil(node.width*node.height/6)});}return node;
 }},Image:TestImage,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>revoked++},FormData:TestFormData,
 fetch:async(url,options)=>{requests++;request=options.body;return {status:413,ok:false,redirected:false};},location:{href:'/create',assign:()=>navigated=true},Promise,Error,Math,Number
});
(async()=>{
 camera.files=Array.from({length:5},()=>({size:8_000_000}));camera.value='original.jpg';camera.events.change();
 await form.events.submit({preventDefault(){}});assert.equal(requests,0,'Submit during compression');
 await new Promise(setImmediate);
 assert.equal(camera.value,'');assert.equal(previews.children.length,5);assert.equal(submit.disabled,false);
 previews.children[0].children[2].events.click();assert.equal(previews.children.length,4);
 await form.events.submit({preventDefault(){}});
 assert.equal(requests,1);assert.equal(request.files.length,4);assert(request.files.every(f=>f.blob.size<=150000&&f.name==='photo'));
 assert(status.textContent.includes('Webserver'));assert.equal(previews.children.length,4);assert.equal(navigated,false);assert(revoked>0);
 console.log('PASS: large camera images compressed before fetch, queue/preview/removal, blocked pending submit, only compact JPEG uploads, 413 preserves selection');
})().catch(error=>{console.error(error);process.exitCode=1;});
