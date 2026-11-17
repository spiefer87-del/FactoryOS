/* All camera/gallery photos are compressed BEFORE any network request. */
document.addEventListener('DOMContentLoaded',()=>{
 const form=document.getElementById('defect-editor');if(!form)return;
 const status=document.getElementById('defect-photo-status'),previews=document.getElementById('defect-photo-previews');
 const submit=form.querySelector('[type=submit]'),inputs=[...form.querySelectorAll('input[type=file]')];
 const saved=Number(form.dataset.savedPhotos)||0,queue=[];
 let processing=Promise.resolve(),busy=0,saving=false;
 const controls=()=>{submit.disabled=busy>0||saving;inputs.forEach(i=>i.disabled=saving);};
 const say=text=>{status.textContent=text;};
 const render=()=>{previews.replaceChildren();queue.forEach(item=>{
  const card=document.createElement('div'),img=document.createElement('img'),button=document.createElement('button'),label=document.createElement('p'),edit=document.createElement('button');
  img.src=item.url;img.alt='Neu ausgewähltes Fehlerfoto';
  label.textContent=Math.ceil(item.blob.size/1000)+' KB – noch nicht gespeichert';
  button.type='button';button.textContent='Foto entfernen';button.disabled=saving||busy>0;
  button.addEventListener('click',()=>{URL.revokeObjectURL(item.url);queue.splice(queue.indexOf(item),1);render();say('Foto aus der Auswahl entfernt.');});
  edit.type='button';edit.textContent='Zuschneiden / Zoomen';edit.disabled=saving||busy>0;
  edit.addEventListener('click',async()=>{
   busy++;controls();render();
   try{const cropped=await cropPhoto(item.source||item.blob);if(cropped){const blob=await compress(cropped);item.source=item.source||item.blob;URL.revokeObjectURL(item.url);item.blob=blob;item.url=URL.createObjectURL(blob);say('Bildausschnitt übernommen – noch nicht gespeichert.');}}
   catch(error){say(error.message||'Foto konnte nicht bearbeitet werden.');}
   finally{busy--;controls();render();}
  });
  card.append(img,label,button,edit);previews.append(card);
 });};
 // Local-only editor: keep the initial image so repeated edits do not accumulate crops.
 async function cropPhoto(blob){
  const url=URL.createObjectURL(blob),photo=new Image();
  let dialog;
  try{
   await new Promise((resolve,reject)=>{photo.onload=resolve;photo.onerror=()=>reject(Error('Foto konnte nicht geöffnet werden.'));photo.src=url;});
   dialog=document.createElement('dialog');dialog.className='defect-crop-dialog';
   dialog.style.cssText='box-sizing:border-box;width:min(94vw,620px);max-height:92dvh;overflow:auto;border:1px solid #cbd5e1;border-radius:16px;padding:20px;color:#0f172a;background:white';
   const heading=document.createElement('h2');heading.textContent='Foto zuschneiden';
   const help=document.createElement('p');help.textContent='Format wählen, hineinzoomen und den Ausschnitt mit den Reglern verschieben. Erst „Übernehmen“ ändert das ausgewählte Foto.';
   const canvas=document.createElement('canvas');canvas.style.cssText='display:block;width:100%;max-height:38vh;object-fit:contain;background:#e2e8f0';
   const format=document.createElement('select');
   [['original','Originalformat'],['1','Quadratisch'],['1.333333','Querformat 4:3'],['0.75','Hochformat 3:4']].forEach(([value,text])=>{const option=document.createElement('option');option.value=value;option.textContent=text;format.append(option);});
   function field(text,node){const label=document.createElement('label');label.textContent=text;label.style.cssText='display:block;margin:14px 0';node.style.cssText='display:block;width:100%;min-height:44px;font-size:16px';label.append(node);dialog.append(label);}
   function slider(min,max,value){const node=document.createElement('input');node.type='range';node.min=min;node.max=max;node.step='0.01';node.value=value;return node;}
   const zoom=slider('1','4','1'),horizontal=slider('0','1','0.5'),vertical=slider('0','1','0.5');
   dialog.append(heading,help,canvas);field('Format',format);field('Zoom',zoom);field('Ausschnitt links / rechts',horizontal);field('Ausschnitt oben / unten',vertical);
   let rect;
   function draw(){
    const w=photo.naturalWidth,h=photo.naturalHeight,ratio=format.value==='original'?w/h:Number(format.value);
    let cw=Math.min(w,h*ratio)/Number(zoom.value),ch=cw/ratio;
    rect={x:(w-cw)*Number(horizontal.value),y:(h-ch)*Number(vertical.value),w:cw,h:ch};
    const scale=Math.min(1,1600/Math.max(cw,ch));canvas.width=Math.max(1,Math.round(cw*scale));canvas.height=Math.max(1,Math.round(ch*scale));
    const ctx=canvas.getContext('2d');if(!ctx)throw Error('Bildbearbeitung ist auf diesem Gerät nicht verfügbar.');
    ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(photo,rect.x,rect.y,rect.w,rect.h,0,0,canvas.width,canvas.height);
   }
   [format,zoom,horizontal,vertical].forEach(node=>node.addEventListener('input',draw));
   const reset=document.createElement('button'),cancel=document.createElement('button'),apply=document.createElement('button');
   reset.type=cancel.type=apply.type='button';reset.textContent='Zurücksetzen';cancel.textContent='Abbrechen';apply.textContent='Übernehmen';apply.className='btn-primary';
   reset.addEventListener('click',()=>{format.value='original';zoom.value='1';horizontal.value=vertical.value='0.5';draw();});
   dialog.append(reset,cancel,apply);document.body.append(dialog);draw();
   return await new Promise(resolve=>{
    cancel.addEventListener('click',()=>resolve(null));dialog.addEventListener('cancel',event=>{event.preventDefault();resolve(null);});
    apply.addEventListener('click',()=>{apply.disabled=true;canvas.toBlob(result=>{if(result)resolve(result);else{apply.disabled=false;help.textContent='Ausschnitt konnte nicht erstellt werden. Bitte erneut versuchen.';}},'image/jpeg',0.9);});
    dialog.showModal();cancel.focus();
   });
  }finally{if(dialog)dialog.remove();photo.src='';URL.revokeObjectURL(url);}
 }
 async function compress(file){
  if(file.size>50*1024*1024)throw Error('Foto größer als 50 MB. Bitte eine kleinere Kameraauflösung wählen.');
  const url=URL.createObjectURL(file),image=new Image();
  try{
   await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Fotoformat nicht lesbar. Bitte JPEG, PNG oder WebP verwenden.'));image.src=url;});
   const scale=Math.min(1,1600/Math.max(image.naturalWidth,image.naturalHeight));
   let width=Math.max(1,Math.round(image.naturalWidth*scale)),height=Math.max(1,Math.round(image.naturalHeight*scale));
   const canvas=document.createElement('canvas');
   while(true){
    canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d');if(!ctx)throw Error('Bildverkleinerung auf diesem Gerät nicht verfügbar.');
    ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);ctx.drawImage(image,0,0,width,height);
    for(const quality of [0.82,0.72,0.62]){
     const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',quality));
     if(!blob)throw Error('Foto konnte nicht verkleinert werden.');
     if(blob.size<=150000)return blob;
    }
    if(Math.max(width,height)<=320)throw Error('Foto konnte nicht ausreichend komprimiert werden.');
    width=Math.max(1,Math.floor(width*0.8));height=Math.max(1,Math.floor(height*0.8));
   }
  }finally{image.src='';URL.revokeObjectURL(url);}
 }
 inputs.forEach(input=>input.addEventListener('change',()=>{
  const files=[...input.files];input.value='';busy++;controls();say('Fotos werden auf dem Gerät verkleinert …');
  processing=processing.then(async()=>{
   for(const file of files){
    if(saved+queue.length>=5)throw Error('Maximal fünf Fotos pro Eintrag. Zuerst ein Foto entfernen.');
    const blob=await compress(file);queue.push({blob,url:URL.createObjectURL(blob)});render();
   }
   say(queue.length+' neue Fotos bereit. Zusammen '+Math.ceil(queue.reduce((n,item)=>n+item.blob.size,0)/1000)+' KB.');
  }).catch(error=>say(error.message)).finally(()=>{busy--;controls();render();});
 }));
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy||saving){say('Bitte warten, die Fotos werden noch verarbeitet.');return;}
  if(!form.reportValidity())return;
  saving=true;controls();render();say('Wird gespeichert …');
  try{
   const data=new FormData(form);data.delete('camera');data.delete('photo');
   queue.forEach((item,i)=>data.append('photo',item.blob,'fehlerfoto-'+(i+1)+'.jpg'));
   const response=await fetch(form.action||location.href,{method:'POST',body:data,credentials:'same-origin'});
   if(response.redirected&&response.ok){location.assign(response.url);return;}
   if(response.status===413)throw Error('Der Webserver erlaubt diesen Upload noch nicht. Bitte weniger Fotos gleichzeitig speichern. Ihre Eingaben bleiben hier erhalten.');
   const html=await response.text(),doc=new DOMParser().parseFromString(html,'text/html');
   throw Error(doc.querySelector('[role=alert]')?.textContent.trim()||'Speichern nicht möglich ('+response.status+'). Bitte Eingaben und Berechtigung prüfen; bei geändertem Eintrag neu laden.');
  }catch(error){say(error.message||'Verbindung unterbrochen. Bitte erneut versuchen.');}
  finally{saving=false;controls();render();}
 });
});
