document.addEventListener("DOMContentLoaded", function(){

let activeMarker = null
let offsetX = 0
let offsetY = 0

function getSVGPoint(svg, clientX, clientY){

    const pt = svg.createSVGPoint()
    pt.x = clientX
    pt.y = clientY

    const screenCTM = svg.getScreenCTM()

    return pt.matrixTransform(screenCTM.inverse())
}

/* ================= CLICK ================= */

svg.addEventListener("click", function(e){

    if(isDragging) return
    if(svg.dataset.status !== "draft") return

    const pt = getSVGPoint(svg, e.clientX, e.clientY)

    const x = pt.x / 100
    const y = pt.y / 100

    document.getElementById("posX").value = x
    document.getElementById("posY").value = y
    document.getElementById("sectionID").value = svg.dataset.section

    document.getElementById("characteristicModal").style.display = "block"

})

/* ================= DRAG ================= */

document.querySelectorAll(".marker").forEach(marker => {

    marker.addEventListener("mousedown", function(e){

        if(marker.dataset.status !== "draft") return

        activeMarker = marker
        isDragging = true

        const svg = marker.closest("svg")

        const pt = getSVGPoint(svg, e.clientX, e.clientY)

        const transform = marker.getAttribute("transform")
        const match = transform.match(/translate\(([^ ]+) ([^ ]+)\)/)

        if(match){
            offsetX = parseFloat(match[1]) - pt.x
            offsetY = parseFloat(match[2]) - pt.y
        }

        e.stopPropagation()
    })

})

document.addEventListener("mousemove", function(e){

    if(!activeMarker) return

    const svg = activeMarker.closest("svg")
    const pt = getSVGPoint(svg, e.clientX, e.clientY)

    let x = pt.x + offsetX
    let y = pt.y + offsetY

    x = Math.max(0, Math.min(100, x))
    y = Math.max(0, Math.min(100, y))

    activeMarker.setAttribute(
        "transform",
        `translate(${x} ${y})`
    )
})

document.addEventListener("mouseup", function(){

    if(!activeMarker) return

    const transform = activeMarker.getAttribute("transform")
    const match = transform.match(/translate\(([^ ]+) ([^ ]+)\)/)

    if(match){

        fetch("/quality/inspection-plans/update_characteristic_position",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                id: activeMarker.dataset.id,
                x: parseFloat(match[1]) / 100,
                y: parseFloat(match[2]) / 100
            })
        })
    }

    activeMarker = null
    isDragging = false
})


/* ================= DELETE ================= */

document.querySelectorAll(".marker").forEach(marker => {

    marker.addEventListener("contextmenu", function(e){

        e.preventDefault()

        if(marker.dataset.status !== "draft") return
        if(!confirm("Marker und Merkmal löschen?")) return

        const id = marker.dataset.id

        // UI sofort entfernen
        marker.remove()

        const row = document.querySelector(`.characteristic-row[data-id="${id}"]`)
        if(row) row.remove()

        // Backend löschen
        fetch("/quality/inspection-plans/delete_characteristic_marker",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({ id: id })
        })
        .then(()=>location.reload())

    })

})

/* ================= ZOOM + PAN ================= */

document.querySelectorAll(".drawing-stage").forEach(stage => {

    let scale = 1
    let translateX = 0
    let translateY = 0

    let startX = 0
    let startY = 0

    let isPanning = false

    let lastTouchDistance = null

    function updateTransform(){
        stage.style.transform =
            `translate(${translateX}px, ${translateY}px) scale(${scale})`
    }

    /* ================= DESKTOP ZOOM ================= */

    stage.addEventListener("wheel", function(e){

        e.preventDefault()

        const zoomIntensity = 0.001
        const delta = e.deltaY

        const newScale = scale - delta * zoomIntensity

        scale = Math.min(Math.max(0.5, newScale), 4)

        updateTransform()

    }, { passive:false })

    /* ================= PAN (MOUSE) ================= */

    stage.addEventListener("mousedown", function(e){
        isPanning = true
        startX = e.clientX - translateX
        startY = e.clientY - translateY
    })

    document.addEventListener("mousemove", function(e){
        if(!isPanning) return

        translateX = e.clientX - startX
        translateY = e.clientY - startY

        updateTransform()
    })

    document.addEventListener("mouseup", function(){
        isPanning = false
    })

    /* ================= TOUCH START ================= */

    stage.addEventListener("touchstart", function(e){

        if(e.touches.length === 1){
            isPanning = true
            startX = e.touches[0].clientX - translateX
            startY = e.touches[0].clientY - translateY
        }

        if(e.touches.length === 2){
            lastTouchDistance = getTouchDistance(e.touches)
        }

    })

    /* ================= TOUCH MOVE ================= */

    stage.addEventListener("touchmove", function(e){

        e.preventDefault()

        // PAN
        if(e.touches.length === 1 && isPanning){

            translateX = e.touches[0].clientX - startX
            translateY = e.touches[0].clientY - startY

            updateTransform()
        }

        // PINCH ZOOM
        if(e.touches.length === 2){

            const distance = getTouchDistance(e.touches)

            if(lastTouchDistance){

                const delta = distance - lastTouchDistance
                const zoomFactor = delta * 0.005

                scale = Math.min(Math.max(0.5, scale + zoomFactor), 4)

                updateTransform()
            }

            lastTouchDistance = distance
        }

    }, { passive:false })

    /* ================= TOUCH END ================= */

    stage.addEventListener("touchend", function(e){

        if(e.touches.length < 2){
            lastTouchDistance = null
        }

        if(e.touches.length === 0){
            isPanning = false
        }

    })

    /* ================= HELPERS ================= */

    function getTouchDistance(touches){

        const dx = touches[0].clientX - touches[1].clientX
        const dy = touches[0].clientY - touches[1].clientY

        return Math.sqrt(dx*dx + dy*dy)
    }

})
