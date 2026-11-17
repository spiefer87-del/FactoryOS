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
  const card=document.createElement('div'),img=document.createElement('img'),button=document.createElement('button'),label=document.createElement('p');
  img.src=item.url;img.alt='Neu ausgewähltes Fehlerfoto';
  label.textContent=Math.ceil(item.blob.size/1000)+' KB – noch nicht gespeichert';
  button.type='button';button.textContent='Foto entfernen';button.disabled=saving;
  button.addEventListener('click',()=>{URL.revokeObjectURL(item.url);queue.splice(queue.indexOf(item),1);render();say('Foto aus der Auswahl entfernt.');});
  card.append(img,label,button);previews.append(card);
 });};
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
  }).catch(error=>say(error.message)).finally(()=>{busy--;controls();});
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
