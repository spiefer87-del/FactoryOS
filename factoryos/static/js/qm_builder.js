document.addEventListener("DOMContentLoaded", function(){

    let activeMarker = null
    let offsetX = 0
    let offsetY = 0

    /* ================= IMAGE DRAG DISABLE ================= */

    document.querySelectorAll(".drawing-img").forEach(img => {
        img.addEventListener("dragstart", e => e.preventDefault())
    })

    /* ================= HELPER ================= */

    function getPixelCoordinates(wrapper, clientX, clientY){

        const img = wrapper.querySelector(".drawing-img")
        const rect = img.getBoundingClientRect()

        const scaleX = img.naturalWidth / rect.width
        const scaleY = img.naturalHeight / rect.height

        const x = (clientX - rect.left) * scaleX
        const y = (clientY - rect.top) * scaleY

        return { x, y }
    }

    /* ================= CLICK ================= */

    document.querySelectorAll(".drawing-wrapper").forEach(wrapper => {

        wrapper.addEventListener("click", function(e){

            const img = wrapper.querySelector(".drawing-img")
            if(!img || img.dataset.status !== "draft") return

            const coords = getPixelCoordinates(wrapper, e.clientX, e.clientY)

            document.getElementById("posX").value = coords.x
            document.getElementById("posY").value = coords.y
            document.getElementById("sectionID").value = img.dataset.section

            document.getElementById("characteristicModal").style.display = "block"
        })
    })

    /* ================= DRAG START ================= */

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

    /* ================= DRAG MOVE ================= */

    document.addEventListener("mousemove", function(e){

        if(!activeMarker) return

        const wrapper = activeMarker.closest(".drawing-wrapper")
        const img = wrapper.querySelector(".drawing-img")
        const rect = img.getBoundingClientRect()

        const scaleX = img.naturalWidth / rect.width
        const scaleY = img.naturalHeight / rect.height

        let x = (e.clientX - rect.left) * scaleX - offsetX * scaleX
        let y = (e.clientY - rect.top) * scaleY - offsetY * scaleY

        x = Math.max(0, Math.min(img.naturalWidth, x))
        y = Math.max(0, Math.min(img.naturalHeight, y))

        activeMarker.style.left = x + "px"
        activeMarker.style.top = y + "px"
    })

    /* ================= DRAG END ================= */

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
            .then(() => location.reload())
        })
    })

})