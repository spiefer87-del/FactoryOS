(() => {
  'use strict';
  const reasons=document.getElementById('deviation-reason');
  if(!reasons)return;
  reasons.addEventListener('change',()=>{
    const target=reasons.selectedOptions[0]?.dataset.orderEditUrl;
    if(!target)return;
    const url=new URL(target,location.origin);
    if(url.origin===location.origin)location.assign(url.href);
  });
})();
