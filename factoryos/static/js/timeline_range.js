(() => {
  'use strict';
  const form=document.getElementById('timeline-range-form');
  if(!form)return;
  const select=form.querySelector('[name="zeitraum"]');
  const fields=document.getElementById('timeline-custom-fields');
  const dates=fields.querySelectorAll('input[type="datetime-local"]');
  function update(){
    const custom=select.value==='custom';fields.hidden=!custom;
    dates.forEach(input=>input.required=custom);
  }
  update();
  select.addEventListener('change',()=>{
    update();
    if(select.value==='custom'){dates[0].focus();return;}
    if(form.requestSubmit)form.requestSubmit();else form.submit();
  });
})();
