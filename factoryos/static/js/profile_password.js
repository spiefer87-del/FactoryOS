document.addEventListener("DOMContentLoaded",function(){
    "use strict";
    const buttons=Array.from(document.querySelectorAll("[data-password-toggle]"));
    function hide(button){const input=document.getElementById(button.dataset.passwordToggle);if(!input)return;input.type="password";button.setAttribute("aria-pressed","false");button.setAttribute("aria-label",button.dataset.passwordLabel+" anzeigen");}
    buttons.forEach(function(button){
        const input=document.getElementById(button.dataset.passwordToggle);if(!input)return;
        button.hidden=false;
        button.addEventListener("click",function(){const show=input.type==="password";input.type=show?"text":"password";button.setAttribute("aria-pressed",String(show));button.setAttribute("aria-label",button.dataset.passwordLabel+(show?" verbergen":" anzeigen"));});
    });
    function hideAll(){buttons.forEach(hide);}
    document.addEventListener("visibilitychange",function(){if(document.hidden)hideAll();});
    window.addEventListener("pagehide",hideAll);
    const form=document.getElementById("personal-password-form");
    if(form)form.addEventListener("submit",hideAll);
});
