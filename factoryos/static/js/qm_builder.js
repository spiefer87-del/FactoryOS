document.addEventListener("DOMContentLoaded",()=>{

initMarkers()
initZoom()
initTooltip()

})


function initMarkers(){

console.log("Marker System geladen")

}

function initZoom(){

document.querySelectorAll(".drawing-wrapper")
.forEach(wrapper=>{

wrapper.addEventListener("wheel",function(e){

e.preventDefault()

})

})

}

function initTooltip(){

const tooltip = document.getElementById("markerTooltip")

if(!tooltip) return

}
