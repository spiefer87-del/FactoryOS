function getDrawingCoordinates(wrapper, clientX, clientY){

const stage = wrapper.querySelector(".drawing-stage")
const img = wrapper.querySelector(".drawing-img")

const rect = img.getBoundingClientRect()

const style = window.getComputedStyle(stage)
const matrix = new DOMMatrix(style.transform)

const scale = matrix.a
const translateX = matrix.e
const translateY = matrix.f

const x = (clientX - rect.left - translateX) / scale
const y = (clientY - rect.top - translateY) / scale

return {
x: x / rect.width,
y: y / rect.height
}

}

document.addEventListener("DOMContentLoaded", function(){

let activeMarker=null
let isDragging=false

document.querySelectorAll(".drawing-wrapper").forEach(function(wrapper){

wrapper.addEventListener("click",function(e){

if(isDragging) return

const img=wrapper.querySelector(".drawing-img")

if(!img || img.dataset.status !== "draft") return

const coords=getDrawingCoordinates(wrapper,e.clientX,e.clientY)

document.getElementById("posX").value=coords.x
document.getElementById("posY").value=coords.y
document.getElementById("sectionID").value=img.dataset.section

document.getElementById("characteristicModal").style.display="block"

})

})

window.closeCharacteristicModal=function(){

document.getElementById("characteristicModal").style.display="none"

}

document.getElementById("characteristicForm")?.addEventListener("submit",function(e){

e.preventDefault()

const data={

section_id:document.getElementById("sectionID").value,
pos_x:document.getElementById("posX").value,
pos_y:document.getElementById("posY").value,

name:document.getElementById("charName").value,
target_value:document.getElementById("charTarget").value,
tolerance_minus:document.getElementById("charTolMinus").value,
tolerance_plus:document.getElementById("charTolPlus").value,
unit:document.getElementById("charUnit").value

}

fetch("/quality/inspection-plans/create_characteristic_with_marker",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)

}).then(()=>location.reload())

})

document.querySelectorAll(".marker").forEach(function(marker){

marker.addEventListener("mousedown",function(e){

if(marker.dataset.status!=="draft") return

activeMarker=marker
isDragging=true

e.stopPropagation()

})

})

document.addEventListener("mousemove",function(e){

if(!activeMarker) return

const wrapper=activeMarker.closest(".drawing-wrapper")

const coords=getDrawingCoordinates(wrapper,e.clientX,e.clientY)

let x=Math.max(0,Math.min(1,coords.x))
let y=Math.max(0,Math.min(1,coords.y))

activeMarker.setAttribute(
"transform",
`translate(${x*100} ${y*100})`
)

})

document.addEventListener("mouseup",function(){

if(!activeMarker) return

const transform=activeMarker.getAttribute("transform")

const match=transform.match(/translate\((.*)\s(.*)\)/)

const x=parseFloat(match[1])/100
const y=parseFloat(match[2])/100

fetch("/quality/inspection-plans/update_characteristic_position",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({

id:activeMarker.dataset.id,
x:x,
y:y

})

})

activeMarker=null

setTimeout(()=>{
isDragging=false
},50)

})

document.querySelectorAll(".detect-features").forEach(btn=>{

btn.addEventListener("click",function(){

const section=btn.dataset.section

fetch(`/quality/inspection-plans/detect_features/${section}`)
.then(res=>res.json())
.then(data=>{

const svg=document.querySelector(
`svg.marker-layer[data-section="${section}"]`
)

data.forEach(circle=>{

const marker=document.createElementNS(
"http://www.w3.org/2000/svg","g"
)

marker.setAttribute(
"transform",
`translate(${circle.x*100} ${circle.y*100})`
)

marker.innerHTML=`
<circle r="2" fill="#3498db"></circle>
`

svg.appendChild(marker)

})

})

})

})

})
