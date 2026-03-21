document.addEventListener("DOMContentLoaded", function(){

let activeMarker = null
let isDragging = false

/* ================= COORDINATES ================= */

function getSVGCoordinates(svg, clientX, clientY){

    const rect = svg.getBoundingClientRect()

    return {
        x: (clientX - rect.left) / rect.width,
        y: (clientY - rect.top) / rect.height
    }
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

/* ================= DRAG START ================= */

document.querySelectorAll(".marker").forEach(marker => {

    marker.addEventListener("mousedown", function(e){

        if(marker.dataset.status !== "draft") return

        activeMarker = marker
        isDragging = true

        document.body.style.userSelect = "none"
        e.stopPropagation()
    })

})

/* ================= DRAG MOVE ================= */

document.addEventListener("mousemove", function(e){

    if(!activeMarker) return

    const svg = activeMarker.closest(".drawing-svg")

    const coords = getSVGCoordinates(svg, e.clientX, e.clientY)

    const width = svg.viewBox.baseVal.width
    const height = svg.viewBox.baseVal.height

    const x = coords.x * width
    const y = coords.y * height

    activeMarker.setAttribute(
        "transform",
        `translate(${x} ${y})`
    )

})

/* ================= DRAG END ================= */

document.addEventListener("mouseup", function(){

    if(!activeMarker) return

    const svg = activeMarker.closest(".drawing-svg")

    const width = svg.viewBox.baseVal.width
    const height = svg.viewBox.baseVal.height

    const transform = activeMarker.getAttribute("transform")
    const match = transform.match(/translate\(([^ ]+) ([^ ]+)\)/)

    if(match){

        const x = parseFloat(match[1]) / width
        const y = parseFloat(match[2]) / height

        fetch("/quality/inspection-plans/update_characteristic_position",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                id: activeMarker.dataset.id,
                x: x,
                y: y
            })
        })
    }

    activeMarker = null
    document.body.style.userSelect = ""

    setTimeout(()=>{ isDragging = false }, 50)

})

})
