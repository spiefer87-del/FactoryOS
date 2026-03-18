document.addEventListener("DOMContentLoaded", function(){

initDrawingMarkers()
initMarkerDrag()
initTableHighlight()
initZoomPan()

})

function initDrawingMarkers(){

document.querySelectorAll(".drawing-wrapper").forEach(function(wrapper){

wrapper.addEventListener("click",function(e){

const img = wrapper.querySelector(".drawing-img")

if(!img) return

if(img.dataset.status !== "draft") return

const rect = img.getBoundingClientRect()

const x = (e.clientX - rect.left) / rect.width
const y = (e.clientY - rect.top) / rect.height

document.getElementById("posX").value = x
document.getElementById("posY").value = y
document.getElementById("sectionID").value = img.dataset.section

document.getElementById("characteristicModal").style.display="block"

})

})

}

function initMarkerDrag(){

let activeMarker=null

document.querySelectorAll(".marker").forEach(function(marker){

marker.addEventListener("mousedown",function(e){

activeMarker = marker
e.stopPropagation()

})

})

document.addEventListener("mousemove",function(e){

if(!activeMarker) return

const wrapper=activeMarker.closest(".drawing-wrapper")
const img=wrapper.querySelector("img")

const rect = img.getBoundingClientRect()

let x = (e.clientX - rect.left) / rect.width
let y = (e.clientY - rect.top) / rect.height

x=Math.max(0,Math.min(1,x))
y=Math.max(0,Math.min(1,y))

activeMarker.setAttribute(
"transform",
`translate(${x*100} ${y*100})`
)

})

document.addEventListener("mouseup",function(){

activeMarker=null

})

}

function initTableHighlight(){

document.querySelectorAll(".marker").forEach(function(marker){

marker.addEventListener("click",function(){

const id=marker.dataset.id

document.querySelectorAll(".characteristic-row")
.forEach(r=>r.classList.remove("row-highlight"))

const row=document.querySelector(
`.characteristic-row[data-id="${id}"]`
)

if(row){

row.classList.add("row-highlight")

row.scrollIntoView({
behavior:"smooth",
block:"center"
})

}

})

})

}

function initZoomPan(){

document.querySelectorAll(".drawing-wrapper").forEach(wrapper=>{

const stage = wrapper.querySelector(".drawing-stage")

let scale=1

wrapper.addEventListener("wheel",function(e){

e.preventDefault()

if(e.deltaY<0) scale+=0.1
else scale-=0.1

scale=Math.max(0.5,Math.min(4,scale))

stage.style.transform=`scale(${scale})`

})

})

}
