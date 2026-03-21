let offsetX = 0
let offsetY = 0

function getDrawingCoordinates(wrapper, clientX, clientY){

    const stage = wrapper.querySelector(".drawing-stage")
    const rect = stage.getBoundingClientRect()

    return {
        x: (clientX - rect.left) / rect.width,
        y: (clientY - rect.top) / rect.height
    }
}

document.addEventListener("DOMContentLoaded", function(){

let activeMarker = null
let isDragging = false

/* ================= CLICK → MARKER SETZEN ================= */

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

/* ================= MODAL ================= */

window.closeCharacteristicModal = function(){
    document.getElementById("characteristicModal").style.display="none"
}

/* ================= SAVE ================= */

const form = document.getElementById("characteristicForm")

if(form){
    form.addEventListener("submit",function(e){

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
}

/* ================= DRAG START ================= */

document.querySelectorAll(".marker").forEach(function(marker){

    marker.addEventListener("mousedown", function(e){

        if(marker.dataset.status !== "draft") return

        activeMarker = marker
        isDragging = true

        const wrapper = marker.closest(".drawing-wrapper")
        const coords = getDrawingCoordinates(wrapper, e.clientX, e.clientY)

        const transform = marker.getAttribute("transform")
        const match = transform.match(/translate\(([^ ]+) ([^ ]+)\)/)

        if(match){
            offsetX = parseFloat(match[1]) / 100 - coords.x
            offsetY = parseFloat(match[2]) / 100 - coords.y
        }

        document.body.style.userSelect = "none"
        e.stopPropagation()
    })

})

/* ================= DRAG MOVE ================= */

document.addEventListener("mousemove", function(e){

    if(!activeMarker) return

    const wrapper = activeMarker.closest(".drawing-wrapper")
    const coords = getDrawingCoordinates(wrapper, e.clientX, e.clientY)

    let x = coords.x + offsetX
    let y = coords.y + offsetY

    x = Math.max(0, Math.min(1, x))
    y = Math.max(0, Math.min(1, y))

    activeMarker.setAttribute(
        "transform",
        `translate(${x * 100} ${y * 100})`
    )
})

/* ================= DRAG END ================= */

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
    document.body.style.userSelect = ""
    setTimeout(()=>{ isDragging = false }, 50)
})

/* ================= DELETE ================= */

document.querySelectorAll(".marker").forEach(function(marker){

    marker.addEventListener("contextmenu",function(e){

        e.preventDefault()

        if(marker.dataset.status !== "draft") return
        if(!confirm("Marker und Merkmal löschen?")) return

        const id = marker.dataset.id

        marker.remove()

        const row = document.querySelector(`.characteristic-row[data-id="${id}"]`)
        if(row) row.remove()

        fetch("/quality/inspection-plans/delete_characteristic_marker",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({id:id})
        }).then(()=>location.reload())

    })

})

/* ================= MARKER → TABELLE ================= */

document.querySelectorAll(".marker").forEach(function(marker){

    marker.addEventListener("click",function(){

        const id = marker.dataset.id

        document.querySelectorAll(".characteristic-row")
        .forEach(r=>r.classList.remove("row-highlight"))

        const row = document.querySelector(`.characteristic-row[data-id="${id}"]`)

        if(row){

            row.classList.add("row-highlight")

            row.scrollIntoView({
                behavior:"smooth",
                block:"center"
            })

        }

    })

})

/* ================= TABELLE → MARKER ================= */

document.querySelectorAll(".characteristic-row").forEach(function(row){

    row.addEventListener("click",function(){

        const id = row.dataset.id

        document.querySelectorAll(".marker")
        .forEach(m=>m.classList.remove("marker-highlight"))

        const marker = document.querySelector(`.marker[data-id="${id}"]`)

        if(marker){

            marker.classList.add("marker-highlight")

            marker.closest(".drawing-wrapper").scrollIntoView({
                behavior:"smooth",
                block:"center"
            })

            setTimeout(()=>{
                marker.classList.remove("marker-highlight")
            },1500)

        }

    })

})

})
