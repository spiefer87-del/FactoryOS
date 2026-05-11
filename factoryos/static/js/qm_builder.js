let isDragging = false
let hasMoved = false
let pressTimer = null
let longPressTriggered = false

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

            if(isDragging) return

            if(hasMoved){
                hasMoved = false   // 🔥 direkt resetten
                return
            }

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

            isDragging = true       
            hasMoved = false         

            const wrapper = marker.closest(".drawing-wrapper")
            const img = wrapper.querySelector(".drawing-img")
            const rect = img.getBoundingClientRect()

            const scaleX = img.naturalWidth / rect.width
            const scaleY = img.naturalHeight / rect.height

            // 🔥 WICHTIG: Offset korrekt berechnen
            const markerX = parseFloat(marker.style.left)
            const markerY = parseFloat(marker.style.top)

            offsetX = (e.clientX - rect.left) * scaleX - markerX
            offsetY = (e.clientY - rect.top) * scaleY - markerY

            document.body.style.userSelect = "none"
            e.stopPropagation()
        })
    })

    /* ================= DRAG MOVE ================= */

    document.addEventListener("mousemove", function(e){

        if(!activeMarker) return

        hasMoved = true

        const wrapper = activeMarker.closest(".drawing-wrapper")
        const img = wrapper.querySelector(".drawing-img")
        const rect = img.getBoundingClientRect()

        const scaleX = img.naturalWidth / rect.width
        const scaleY = img.naturalHeight / rect.height

        let x = (e.clientX - rect.left) * scaleX - offsetX
        let y = (e.clientY - rect.top) * scaleY - offsetY

        x = Math.max(0, Math.min(img.naturalWidth, x))
        y = Math.max(0, Math.min(img.naturalHeight, y))

        // 🔥 NUR PIXEL (kein % mehr!)
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

        setTimeout(() => {
            isDragging = false
            hasMoved = false   // ✅ DAS hat gefehlt
        }, 50)
    })

    /* ================= ROTATE + DELETE ================= */

    document.querySelectorAll(".marker").forEach(marker => {
    
        // Browser Kontextmenü deaktivieren
        marker.addEventListener("contextmenu", function(e){
            e.preventDefault()
        })
    
        // ================= RIGHT CLICK START =================
    
        marker.addEventListener("mousedown", function(e){
    
            // nur rechte Maustaste
            if(e.button !== 2) return
    
            if(marker.dataset.status !== "draft") return
    
            e.preventDefault()
    
            longPressTriggered = false
    
            // LONG PRESS = DELETE
            pressTimer = setTimeout(() => {
    
                longPressTriggered = true
    
                if(!confirm("Marker und Merkmal löschen?")) return
    
                fetch("/quality/inspection-plans/delete_characteristic_marker",{
                    method:"POST",
                    headers:{
                        "Content-Type":"application/json"
                    },
                    body:JSON.stringify({
                        id: marker.dataset.id
                    })
                })
                .then(() => location.reload())
    
            }, 700)
    
        })
    
        // ================= RIGHT CLICK END =================
    
        marker.addEventListener("mouseup", function(e){
    
            if(e.button !== 2) return
    
            clearTimeout(pressTimer)
    
            // wenn delete schon ausgelöst wurde
            if(longPressTriggered) return
    
            // ================= ROTATE =================
    
            let rotation = parseFloat(
                marker.dataset.rotation || 0
            )
    
            rotation += 15
    
            if(rotation >= 360){
                rotation = 0
            }
    
            // dataset speichern
            marker.dataset.rotation = rotation
            
            // Rotator drehen
            const rotator = marker.querySelector(".marker-rotator")
            
            if(rotator){
                rotator.style.transform =
                    `rotate(${rotation}deg)`
            }
    
            // DB speichern
            fetch("/quality/inspection-plans/rotate_characteristic_marker",{
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    id: marker.dataset.id,
                    rotation: rotation
                })
            })
    
        })
    
    })

})
