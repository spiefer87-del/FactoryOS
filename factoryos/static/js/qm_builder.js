document.addEventListener("DOMContentLoaded", function(){

    let activeMarker = null
    let offsetX = 0
    let offsetY = 0
    let isDragging = false   // 🔥 Click-Schutz

    /* ================= IMAGE DRAG DISABLE ================= */

    document.querySelectorAll(".drawing-img").forEach(img => {
        img.addEventListener("dragstart", e => e.preventDefault())
    })

    /* ================= HELPER ================= */

    function getImageCoordinates(wrapper, clientX, clientY){

        const img = wrapper.querySelector(".drawing-img")
        const rect = img.getBoundingClientRect()

        const x = (clientX - rect.left)
        const y = (clientY - rect.top)

        return {
            x: x,
            y: y,
            relX: x / rect.width,
            relY: y / rect.height
        }
    }

    /* ================= CLICK ================= */

    document.querySelectorAll(".drawing-wrapper").forEach(wrapper => {

        wrapper.addEventListener("click", function(e){

            if(isDragging) return   // 🔥 verhindert Ghost-Click nach Drag

            const img = wrapper.querySelector(".drawing-img")
            if(!img || img.dataset.status !== "draft") return

            const coords = getImageCoordinates(wrapper, e.clientX, e.clientY)

            document.getElementById("posX").value = coords.relX
            document.getElementById("posY").value = coords.relY
            document.getElementById("sectionID").value = img.dataset.section

            document.getElementById("characteristicModal").style.display = "block"
        })
    })

    /* ================= DRAG START ================= */

    document.querySelectorAll(".marker").forEach(marker => {

        marker.addEventListener("mousedown", function(e){

            if(marker.dataset.status !== "draft") return

            activeMarker = marker
            isDragging = true

            const stage = marker.closest(".drawing-stage")
            const scale = stage._scale || 1

            const rect = marker.getBoundingClientRect()

            offsetX = e.clientX - rect.left
            offsetY = e.clientY - rect.top

            document.body.style.userSelect = "none"
            e.stopPropagation()
        })
    })

    /* ================= DRAG MOVE ================= */

    document.addEventListener("mousemove", function(e){

        if(!activeMarker) return

        const wrapper = activeMarker.closest(".drawing-wrapper")
        const img = wrapper.querySelector(".drawing-img")
        const stage = wrapper.querySelector(".drawing-stage")

        const rect = img.getBoundingClientRect()

        let x = e.clientX - rect.left - offsetX
        let y = e.clientY - rect.top - offsetY

        x = Math.max(0, Math.min(rect.width, x))
        y = Math.max(0, Math.min(rect.height, y))

        const relX = x / rect.width
        const relY = y / rect.height

        activeMarker.style.left = (relX * 100) + "%"
        activeMarker.style.top = (relY * 100) + "%"
    })

    /* ================= DRAG END ================= */

    document.addEventListener("mouseup", function(){

        if(!activeMarker) return

        const relX = parseFloat(activeMarker.style.left) / 100
        const relY = parseFloat(activeMarker.style.top) / 100

        fetch("/quality/inspection-plans/update_characteristic_position",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                id: activeMarker.dataset.id,
                x: relX,
                y: relY
            })
        })

        activeMarker = null
        document.body.style.userSelect = ""

        // 🔥 wichtig für Click-Schutz
        setTimeout(()=>{ isDragging = false }, 50)
    })

    /* ================= DELETE ================= */

    document.querySelectorAll(".marker").forEach(marker => {

        marker.addEventListener("contextmenu", function(e){

            e.preventDefault()

            if(marker.dataset.status !== "draft") return
            if(!confirm("Marker und Merkmal löschen?")) return

            const id = marker.dataset.id

            fetch("/quality/inspection-plans/delete_characteristic_marker",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({ id: id })
            })
            .then(res => {
                if(!res.ok) throw new Error("Delete failed")

                marker.remove()

                const row = document.querySelector(`.characteristic-row[data-id="${id}"]`)
                if(row) row.remove()
            })
            .catch(err => {
                console.error(err)
                alert("Fehler beim Löschen")
            })
        })
    })

    /* ================= ZOOM ================= */

    document.querySelectorAll(".drawing-stage").forEach(stage => {

        const img = stage.querySelector(".drawing-img")

        let scale = 1

        function applyZoom(){
            stage.style.transform = `scale(${scale})`
            stage.style.transformOrigin = "top left"
            stage._scale = scale   // 🔥 wichtig für Drag
        }

        if(img.complete){
            applyZoom()
        } else {
            img.onload = applyZoom
        }

        const wrapper = stage.closest(".qm-drawing-area")

        wrapper.querySelector(".zoom-in").addEventListener("click", () => {
            scale = Math.min(scale + 0.2, 3)
            applyZoom()
        })

        wrapper.querySelector(".zoom-out").addEventListener("click", () => {
            scale = Math.max(scale - 0.2, 0.5)
            applyZoom()
        })

        wrapper.querySelector(".zoom-reset").addEventListener("click", () => {
            scale = 1
            applyZoom()
        })

    })

})