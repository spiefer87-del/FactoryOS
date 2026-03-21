document.addEventListener("DOMContentLoaded", function(){

let activeMarker = null
let offsetX = 0
let offsetY = 0

function getSVGCoordinates(svg, clientX, clientY){

    const rect = svg.getBoundingClientRect()

    const x = (clientX - rect.left) / rect.width
    const y = (clientY - rect.top) / rect.height

    return { x, y }
}

/* ================= CLICK → MARKER ================= */

document.querySelectorAll(".drawing-svg").forEach(function(svg){

    svg.addEventListener("click", function(e){

        if(isDragging) return

        if(svg.dataset.status !== "draft") return

        const coords = getSVGCoordinates(svg, e.clientX, e.clientY)

        document.getElementById("posX").value = coords.x
        document.getElementById("posY").value = coords.y
        document.getElementById("sectionID").value = svg.dataset.section

        document.getElementById("characteristicModal").style.display = "block"

    })

})

/* ================= DRAG ================= */

document.querySelectorAll(".marker").forEach(marker => {

    marker.addEventListener("mousedown", function(e){

        if(marker.dataset.status !== "draft") return

        activeMarker = marker

        const rect = marker.getBoundingClientRect()

        offsetX = e.clientX - rect.left
        offsetY = e.clientY - rect.top

        document.body.style.userSelect = "none"
        e.stopPropagation()
    })

})

document.addEventListener("mousemove", function(e){

    if(!activeMarker) return

    const wrapper = activeMarker.closest(".drawing-wrapper")
    const coords = getImageCoordinates(wrapper, e.clientX, e.clientY)

    activeMarker.style.left = coords.x + "px"
    activeMarker.style.top = coords.y + "px"

})

document.addEventListener("mouseup", function(){

    if(!activeMarker) return

    const x = parseFloat(activeMarker.style.left)
    const y = parseFloat(activeMarker.style.top)

    fetch("/quality/inspection-plans/update_characteristic_position",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            id: activeMarker.dataset.id,
            x: x,
            y: y
        })
    })

    activeMarker = null
    document.body.style.userSelect = ""
})

})
