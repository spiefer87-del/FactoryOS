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
let isDragging = false

/* ================= CLICK ================= */

document.querySelectorAll(".drawing-wrapper").forEach(function(wrapper){

wrapper.addEventListener("click",function(e){

if(isDragging) return

const img = wrapper.querySelector(".drawing-img")
if(!img || img.dataset.status !== "draft") return

const coords = getDrawingCoordinates(wrapper, e.clientX, e.clientY)

document.getElementById("posX").value = coords.x
document.getElementById("posY").value = coords.y
document.getElementById("sectionID").value = img.dataset.section

document.getElementById("characteristicModal").style.display="block"

})

})

/* ================= SAVE ================= */

document.getElementById("characteristicForm").addEventListener("submit",function(e){

e.preventDefault()

fetch("/quality/inspection-plans/create_characteristic_with_marker",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({

section_id:document.getElementById("sectionID").value,
pos_x:document.getElementById("posX").value,
pos_y:document.getElementById("posY").value,

name:document.getElementById("charName").value,
target_value:document.getElementById("charTarget").value,
tolerance_minus:document.getElementById("charTolMinus").value,
tolerance_plus:document.getElementById("charTolPlus").value,
unit:document.getElementById("charUnit").value

})

}).then(()=>location.reload())

})

/* ================= DRAG ================= */

document.querySelectorAll(".marker").forEach(function(marker){

marker.addEventListener("mousedown",function(e){

if(marker.dataset.status!=="draft") return

activeMarker = marker
isDragging = true
e.stopPropagation()

})

})

document.addEventListener("mousemove",function(e){

if(!activeMarker) return

const wrapper=activeMarker.closest(".drawing-wrapper")

const coords = getDrawingCoordinates(wrapper, e.clientX, e.clientY)

let x = Math.max(0,Math.min(1,coords.x))
let y = Math.max(0,Math.min(1,coords.y))

activeMarker.setAttribute(
"transform",
`translate(${x*100} ${y*100})`
)

})

document.addEventListener("mouseup",function(){

if(!activeMarker) return

const transform=activeMarker.getAttribute("transform")
const match=transform.match(/translate\((.*)\s(.*)\)/)

fetch("/quality/inspection-plans/update_characteristic_position",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({

id:activeMarker.dataset.id,
x:parseFloat(match[1])/100,
y:parseFloat(match[2])/100

})

})

activeMarker = null

setTimeout(()=>{ isDragging=false },50)

})

/* ================= DELETE ================= */

document.querySelectorAll(".marker").forEach(function(marker){

marker.addEventListener("contextmenu",function(e){

e.preventDefault()

if(marker.dataset.status!=="draft") return
if(!confirm("Marker löschen?")) return

fetch("/quality/inspection-plans/delete_characteristic_marker",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({id:marker.dataset.id})

}).then(()=>location.reload())

})

})

})
