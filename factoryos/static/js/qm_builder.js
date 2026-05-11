let isDragging = false
let hasMoved = false
let pressTimer = null
let longPressTriggered = false

document.addEventListener("DOMContentLoaded", function(){

    // ======================================
    // AUTO MODAL STATUS LADEN
    // ======================================

    const autoOpenCheckbox =
        document.getElementById("autoOpenModal")

    if(autoOpenCheckbox){

        const saved =
            localStorage.getItem("qm_auto_open_modal")

        if(saved !== null){

            autoOpenCheckbox.checked =
                saved === "true"
        }
    }

    if(autoOpenCheckbox){

        autoOpenCheckbox.addEventListener(
            "change",
            function(){

                localStorage.setItem(
                    "qm_auto_open_modal",
                    autoOpenCheckbox.checked
                )
            }
        )
    }

    let activeMarker = null
    let offsetX = 0
    let offsetY = 0

    // ======================================
    // ZOOM STATE HELPER
    // ======================================

    function saveZoomState(
        storageKey,
        area,
        zoom,
        extra = {}
    ){

        const existing =
            JSON.parse(
                localStorage.getItem(storageKey) || "{}"
            )

        localStorage.setItem(
            storageKey,
            JSON.stringify({

                ...existing,

                ...extra,

                zoom: zoom,

                scrollLeft: area.scrollLeft,

                scrollTop: area.scrollTop
            })
        )
    }

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
                hasMoved = false
                return
            }

            const img = wrapper.querySelector(".drawing-img")

            if(!img || img.dataset.status !== "draft"){
                return
            }

            const coords = getPixelCoordinates(
                wrapper,
                e.clientX,
                e.clientY
            )

            const autoOpen =
                document.getElementById("autoOpenModal")

            // ==========================================
            // POPUP MODUS
            // ==========================================

            if(autoOpen && autoOpen.checked){

                document.getElementById("posX").value =
                    coords.x

                document.getElementById("posY").value =
                    coords.y

                document.getElementById("sectionID").value =
                    img.dataset.section

                document.getElementById(
                    "characteristicModal"
                ).style.display = "block"
            }

            // ==========================================
            // QUICK MARKER MODE
            // ==========================================

            else{

                fetch("/quality/inspection-plans/add_point",{
                    method:"POST",
                    headers:{
                        "Content-Type":"application/json"
                    },
                    body:JSON.stringify({
                        section_id: img.dataset.section,
                        pos_x: coords.x,
                        pos_y: coords.y
                    })
                })
                .then(() => {

                    const area =
                        wrapper.closest(".qm-drawing-area")

                    if(area){

                        const allAreas =
                            document.querySelectorAll(
                                ".qm-drawing-area"
                            )

                        const areaIndex =
                            Array.from(allAreas)
                            .indexOf(area)

                        const storageKey =
                            `qm_zoom_state_${areaIndex}`

                        const existing =
                            JSON.parse(
                                localStorage.getItem(storageKey)
                                || "{}"
                            )

                        saveZoomState(
                            storageKey,
                            area,
                            existing.zoom || 1,
                            {
                                lastMarkerX: coords.x,
                                lastMarkerY: coords.y
                            }
                        )
                    }

                    location.reload()
                })
            }
        })
    })

    /* ================= DRAG START ================= */

    document.querySelectorAll(".marker").forEach(marker => {

        marker.addEventListener("mousedown", function(e){

            if(marker.dataset.status !== "draft") return

            activeMarker = marker

            isDragging = true
            hasMoved = false

            const wrapper =
                marker.closest(".drawing-wrapper")

            const img =
                wrapper.querySelector(".drawing-img")

            const rect =
                img.getBoundingClientRect()

            const scaleX =
                img.naturalWidth / rect.width

            const scaleY =
                img.naturalHeight / rect.height

            const markerX =
                parseFloat(marker.style.left)

            const markerY =
                parseFloat(marker.style.top)

            offsetX =
                (e.clientX - rect.left) * scaleX
                - markerX

            offsetY =
                (e.clientY - rect.top) * scaleY
                - markerY

            document.body.style.userSelect = "none"

            e.stopPropagation()
        })
    })

    /* ================= DRAG MOVE ================= */

    document.addEventListener("mousemove", function(e){

        if(!activeMarker) return

        hasMoved = true

        const wrapper =
            activeMarker.closest(".drawing-wrapper")

        const img =
            wrapper.querySelector(".drawing-img")

        const rect =
            img.getBoundingClientRect()

        const scaleX =
            img.naturalWidth / rect.width

        const scaleY =
            img.naturalHeight / rect.height

        let x =
            (e.clientX - rect.left) * scaleX
            - offsetX

        let y =
            (e.clientY - rect.top) * scaleY
            - offsetY

        x = Math.max(
            0,
            Math.min(img.naturalWidth, x)
        )

        y = Math.max(
            0,
            Math.min(img.naturalHeight, y)
        )

        activeMarker.style.left = x + "px"
        activeMarker.style.top = y + "px"
    })

    /* ================= DRAG END ================= */

    document.addEventListener("mouseup", function(){

        if(!activeMarker) return

        const x =
            parseFloat(activeMarker.style.left)

        const y =
            parseFloat(activeMarker.style.top)

        fetch(
            "/quality/inspection-plans/update_characteristic_position",
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    id: activeMarker.dataset.id,
                    x: x,
                    y: y
                })
            }
        )

        activeMarker = null

        document.body.style.userSelect = ""

        setTimeout(() => {

            isDragging = false
            hasMoved = false

        }, 50)
    })

    /* ================= ROTATE + DELETE ================= */

    document.querySelectorAll(".marker").forEach(marker => {

        marker.addEventListener("contextmenu", function(e){

            e.preventDefault()

        })

        /* ================= DOUBLE CLICK EDIT ================= */

        marker.addEventListener("dblclick", function(e){

            e.stopPropagation()

            const id = marker.dataset.id

            const row = document.querySelector(
                `.characteristic-row[data-id="${id}"]`
            )

            if(row){

                row.scrollIntoView({
                    behavior:"smooth",
                    block:"center"
                })

                row.classList.add("table-warning")

                setTimeout(() => {

                    row.classList.remove("table-warning")

                }, 2000)
            }
        })

        // ================= RIGHT CLICK START =================

        marker.addEventListener("mousedown", function(e){

            if(e.button !== 2) return

            if(marker.dataset.status !== "draft") return

            e.preventDefault()

            longPressTriggered = false

            pressTimer = setTimeout(() => {

                longPressTriggered = true

                if(!confirm(
                    "Marker und Merkmal löschen?"
                )) return

                fetch(
                    "/quality/inspection-plans/delete_characteristic_marker",
                    {
                        method:"POST",
                        headers:{
                            "Content-Type":"application/json"
                        },
                        body:JSON.stringify({
                            id: marker.dataset.id
                        })
                    }
                )
                .then(() => location.reload())

            }, 700)
        })

        // ================= RIGHT CLICK END =================

        marker.addEventListener("mouseup", function(e){

            if(e.button !== 2) return

            clearTimeout(pressTimer)

            if(longPressTriggered) return

            let rotation =
                parseFloat(
                    marker.dataset.rotation || 0
                )

            rotation += 15

            if(rotation >= 360){
                rotation = 0
            }

            marker.dataset.rotation = rotation

            marker.style.setProperty(
                "--rotation",
                rotation + "deg"
            )

            marker.style.transform =
                `translate(-50%, -50%) rotate(${rotation}deg)`

            fetch(
                "/quality/inspection-plans/rotate_characteristic_marker",
                {
                    method:"POST",
                    headers:{
                        "Content-Type":"application/json"
                    },
                    body:JSON.stringify({
                        id: marker.dataset.id,
                        rotation: rotation
                    })
                }
            )
        })
    })

    /* ================= ZOOM ================= */

    document.querySelectorAll(".qm-drawing-area")
    .forEach((area, index) => {

        const stage =
            area.querySelector(".drawing-stage")

        if(!stage) return

        const storageKey =
            `qm_zoom_state_${index}`

        let zoom = 1

        const savedState =
            localStorage.getItem(storageKey)

        if(savedState){

            try{

                const parsed =
                    JSON.parse(savedState)

                zoom = parsed.zoom || 1

                stage.style.transform =
                    `scale(${zoom})`

                setTimeout(() => {

                    area.scrollLeft =
                        parsed.scrollLeft || 0

                    area.scrollTop =
                        parsed.scrollTop || 0

                }, 50)

            }catch(err){

                console.log(err)
            }
        }

        // ==========================================
        // APPLY ZOOM
        // ==========================================

        function applyZoom(){

            stage.style.transform =
                `scale(${zoom})`

            saveZoomState(
                storageKey,
                area,
                zoom
            )
        }

        // initial anwenden
        applyZoom()

        // ==========================================
        // BUTTONS
        // ==========================================

        const section =
            area.closest(".qm-section")

        const zoomInBtn =
            section.querySelector(".zoom-in")

        const zoomOutBtn =
            section.querySelector(".zoom-out")

        const resetBtn =
            section.querySelector(".zoom-reset")

        // ==========================================
        // ZOOM IN
        // ==========================================

        zoomInBtn?.addEventListener("click", () => {

            zoom += 0.2

            if(zoom > 4){
                zoom = 4
            }

            applyZoom()
        })

        // ==========================================
        // ZOOM OUT
        // ==========================================

        zoomOutBtn?.addEventListener("click", () => {

            zoom -= 0.2

            if(zoom < 0.4){
                zoom = 0.4
            }

            applyZoom()
        })

        // ==========================================
        // RESET
        // ==========================================

        resetBtn?.addEventListener("click", () => {

            zoom = 1

            area.scrollLeft = 0
            area.scrollTop = 0

            applyZoom()
        })

        // ==========================================
        // SCROLL SPEICHERN
        // ==========================================

        area.addEventListener("scroll", () => {

            saveZoomState(
                storageKey,
                area,
                zoom
            )
        })
    })
})
