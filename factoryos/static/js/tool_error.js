// ======================================================
// Tool Error
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // DOM
    // ==================================================

    const form = document.querySelector("form");

    const toolInput = document.getElementById("toolSearch");
    const hiddenToolId = document.getElementById("tool_id");
    const toolDropdown = document.getElementById("toolDropdown");

    const toolStatus = document.getElementById("tool_status");

    const presetSelect = document.getElementById("errorPreset");
    const errorInput = document.getElementById("error_type");

    const tempInput = document.getElementById("temp_id");
    const toolErrorId = document.getElementById("tool_error_id")?.value || "";
    const markerEditorDescription = document.getElementById("markerEditorDescription");

    // ==================================================
    // TEMP ID (nur Create)
    // ==================================================

    let tempId = null;

    if (!toolErrorId) {

        tempId = crypto.randomUUID();

        if (tempInput) {
            tempInput.value = tempId;
        }

    }

    // ==================================================
    // TomSelect deaktivieren
    // ==================================================

    if (toolInput?.tomselect) {
        toolInput.tomselect.destroy();
    }

    // ==================================================
    // Tool Search
    // ==================================================

    let currentResults = [];
    let currentFocus = -1;
    let timeout = null;

    function selectTool(index) {

        const tool = currentResults[index];

        if (!tool) return;

        toolInput.value = tool.text;
        hiddenToolId.value = tool.id;

        toolDropdown.style.display = "none";

        if (toolStatus && tool.status) {
            toolStatus.value = tool.status;
        }

    }

    function setActive(items) {

        if (!items.length) return;

        items.forEach(i => i.classList.remove("active"));

        if (currentFocus >= items.length)
            currentFocus = 0;

        if (currentFocus < 0)
            currentFocus = items.length - 1;

        items[currentFocus].classList.add("active");

    }

    if (toolInput && toolDropdown) {

        toolInput.addEventListener("input", () => {

            clearTimeout(timeout);

            hiddenToolId.value = "";

            if (toolInput.value.length < 2) {

                toolDropdown.style.display = "none";
                return;

            }

            timeout = setTimeout(async () => {

                try {

                    const res = await fetch(
                        `/masterdata/tools/api/search?q=${toolInput.value}`
                    );

                    const data = await res.json();

                    currentResults = data.results || [];
                    currentFocus = -1;

                    toolDropdown.innerHTML = "";

                    if (!currentResults.length) {

                        toolDropdown.style.display = "none";
                        return;

                    }

                    currentResults.forEach((tool, index) => {

                        const div = document.createElement("div");

                        div.className = "dropdown-item";
                        div.textContent = tool.text;

                        div.onclick = () => selectTool(index);

                        toolDropdown.appendChild(div);

                    });

                    toolDropdown.style.display = "block";

                }

                catch (err) {

                    console.error(err);

                }

            }, 250);

        });

        toolInput.addEventListener("keydown", e => {

            const items = toolDropdown.querySelectorAll(".dropdown-item");

            if (e.key === "ArrowDown") {

                currentFocus++;
                setActive(items);

                e.preventDefault();

            }

            if (e.key === "ArrowUp") {

                currentFocus--;

                setActive(items);

                e.preventDefault();

            }

            if (e.key === "Enter") {

                if (currentFocus > -1) {

                    e.preventDefault();

                    items[currentFocus].click();

                }

                else if (currentResults.length) {

                    e.preventDefault();

                    selectTool(0);

                }

            }

        });

        document.addEventListener("click", e => {

            if (
                !toolInput.contains(e.target) &&
                !toolDropdown.contains(e.target)
            ) {

                toolDropdown.style.display = "none";

            }

        });

    }

    // ==================================================
    // Formular prüfen
    // ==================================================

    if (form) {

        form.addEventListener("submit", async e => {

            if (hiddenToolId.value)
                return;

            e.preventDefault();

            const res = await fetch(
                `/masterdata/tools/api/search?q=${toolInput.value}`
            );

            const data = await res.json();

            if (!data.results.length) {

                alert("Werkzeug nicht gefunden");

                return;

            }

            hiddenToolId.value = data.results[0].id;

            form.submit();

        });

    }

    // ==================================================
    // Presets
    // ==================================================

    if (presetSelect && errorInput) {

        presetSelect.addEventListener("change", () => {

            if (presetSelect.value)
                errorInput.value = presetSelect.value;

        });

    }

  
    // ==================================================
    // IMAGE MODULE
    // ==================================================

    const imageInput = document.getElementById("imageInput");
    const previewImage = document.getElementById("previewImage");
    const previewWrapper = document.getElementById("previewWrapper");

    const uploadBtn = document.getElementById("uploadBtn");
    const imageDescription = document.getElementById("imageDescription");
    const gallery = document.getElementById("imageGallery");

    const markerEditorModal =
        document.getElementById("markerEditorModal");
    
    const markerEditorImage =
        document.getElementById("markerEditorImage");
    
    const markerEditorWrapper =
        document.getElementById("markerEditorWrapper");
    
    const saveMarkerBtn =
        document.getElementById("saveMarkerBtn");
    
    const cancelMarkerBtn =
        document.getElementById("cancelMarkerBtn");

    const markerX = document.getElementById("marker_x");
    const markerY = document.getElementById("marker_y");
    const markerPx = document.getElementById("marker_px");
    const markerPy = document.getElementById("marker_py");

    let currentMarker = null;

    if (
        imageInput &&
        previewImage &&
        previewWrapper
    ) {

        // ==========================================
        // Vorschau
        // ==========================================

        imageInput.addEventListener("change", e => {

            const file = e.target.files[0];

            if (!file)
                return;

            const reader = new FileReader();

            reader.onload = ev => {

                previewImage.src = ev.target.result;
                previewImage.style.display = "block";

            };

            reader.readAsDataURL(file);

        });

        // ==========================================
        // Marker setzen
        // ==========================================

        function createMarker(left, top) {

            if (currentMarker)
                currentMarker.remove();

            const marker = document.createElement("div");

            marker.className = "marker-advanced";

            marker.innerHTML = `
                <div class="marker-circle">1</div>
                <div class="marker-arrow"></div>
            `;

            marker.style.left = left + "px";
            marker.style.top = top + "px";

            previewWrapper.appendChild(marker);

            currentMarker = marker;

            enableMarkerDrag(marker);

        }

        function setMarker(clientX, clientY) {

            const rect = previewImage.getBoundingClientRect();

            const relX = Math.max(
                0,
                Math.min(clientX - rect.left, rect.width)
            );

            const relY = Math.max(
                0,
                Math.min(clientY - rect.top, rect.height)
            );

            const xp = relX / rect.width;
            const yp = relY / rect.height;

            markerX.value = xp;
            markerY.value = yp;

            markerPx.value = Math.round(
                xp * previewImage.naturalWidth
            );

            markerPy.value = Math.round(
                yp * previewImage.naturalHeight
            );

            createMarker(
                relX - 18,
                relY
            );

        }

        previewImage.addEventListener("click", e => {

            setMarker(
                e.clientX,
                e.clientY
            );

        });

        previewImage.addEventListener("touchstart", e => {

            e.preventDefault();

            const t = e.touches[0];

            setMarker(
                t.clientX,
                t.clientY
            );

        });

        // ==========================================
        // Marker verschieben
        // ==========================================

        function enableMarkerDrag(marker) {

            let dragging = false;

            marker.addEventListener("mousedown", e => {

                dragging = true;
                e.preventDefault();

            });

            marker.addEventListener("touchstart", e => {

                dragging = true;
                e.preventDefault();

            });

            document.addEventListener("mouseup", () => {

                dragging = false;

            });

            document.addEventListener("touchend", () => {

                dragging = false;

            });

            function move(clientX, clientY) {

                if (!dragging)
                    return;

                const rect = previewImage.getBoundingClientRect();

                const relX = Math.max(
                    0,
                    Math.min(clientX - rect.left, rect.width)
                );

                const relY = Math.max(
                    0,
                    Math.min(clientY - rect.top, rect.height)
                );

                const xp = relX / rect.width;
                const yp = relY / rect.height;

                markerX.value = xp;
                markerY.value = yp;

                markerPx.value = Math.round(
                    xp * previewImage.naturalWidth
                );

                markerPy.value = Math.round(
                    yp * previewImage.naturalHeight
                );

                marker.style.left = (relX - 18) + "px";
                marker.style.top = relY + "px";

            }

            document.addEventListener("mousemove", e => {

                move(
                    e.clientX,
                    e.clientY
                );

            });

            document.addEventListener("touchmove", e => {

                if (!dragging)
                    return;

                const t = e.touches[0];

                move(
                    t.clientX,
                    t.clientY
                );

            });

        }

        // ==========================================
        // Upload
        // ==========================================

        uploadBtn?.addEventListener("click", () => {

            const file = imageInput.files[0];

            if (!file) {

                alert("Bitte Bild auswählen");
                return;

            }

            if (!markerX.value) {

                alert("Bitte Marker setzen");
                return;

            }

            const formData = new FormData();

            formData.append("image", file);

            formData.append("marker_x", markerX.value);
            formData.append("marker_y", markerY.value);

            formData.append("marker_px", markerPx.value);
            formData.append("marker_py", markerPy.value);

            formData.append(
                "description",
                imageDescription.value
            );

            if (toolErrorId) {

                formData.append(
                    "tool_error_id",
                    toolErrorId
                );

            }

            else {

                formData.append(
                    "temp_id",
                    tempId
                );

            }

            fetch("/tool-errors/upload_temp_image", {

                method: "POST",

                body: formData

            })

            .then(r => r.json())

            .then(data => {

                if (!data.success) {

                    alert("Upload fehlgeschlagen");
                    return;

                }

                gallery.insertAdjacentHTML(
                    "beforeend",
                    data.html
                );

                imageInput.value = "";

                previewImage.style.display = "none";

                imageDescription.value = "";

                markerX.value = "";
                markerY.value = "";

                markerPx.value = "";
                markerPy.value = "";

                currentMarker?.remove();
                currentMarker = null;

            });

        });
        }
    
        // ==================================================
        // Image Card Buttons
        // ==================================================
        let currentEditImage = null;
        let currentEditMarker = null;
        
        function openMarkerEditor(image) {

            currentEditImage = image;
            markerEditorDescription.value = image.description || "";
        
            markerEditorImage.onload = () => {
        
                markerEditorModal.classList.remove("hidden");
        
                currentEditMarker?.remove();
        
                const marker = document.createElement("div");
        
                marker.className = "marker-advanced";
        
                marker.innerHTML = `
                    <div class="marker-circle">1</div>
                    <div class="marker-arrow"></div>
                `;
        
                const width = markerEditorImage.offsetWidth;
                const height = markerEditorImage.offsetHeight;
        
                marker.style.left =
                    (image.marker_x * width - 18) + "px";
        
                marker.style.top =
                    (image.marker_y * height) + "px";
        
                markerEditorWrapper.appendChild(marker);
        
                currentEditMarker = marker;

                enableEditorDrag(marker);
        
            };
        
            markerEditorImage.src = image.image_url;
        
        }

        function enableEditorDrag(marker) {

            let dragging = false;
        
            marker.addEventListener("mousedown", e => {
                dragging = true;
                e.preventDefault();
            });
        
            marker.addEventListener("touchstart", e => {
                dragging = true;
                e.preventDefault();
            });
        
            document.addEventListener("mouseup", () => {
                dragging = false;
            });
        
            document.addEventListener("touchend", () => {
                dragging = false;
            });
        
            function move(clientX, clientY) {
        
                if (!dragging)
                    return;
        
                const rect =
                    markerEditorImage.getBoundingClientRect();
        
                const relX = Math.max(
                    0,
                    Math.min(clientX - rect.left, rect.width)
                );
        
                const relY = Math.max(
                    0,
                    Math.min(clientY - rect.top, rect.height)
                );
        
                const xp = relX / rect.width;
                const yp = relY / rect.height;
        
                currentEditImage.marker_x = xp;
                currentEditImage.marker_y = yp;
        
                currentEditImage.marker_px =
                    Math.round(
                        xp * markerEditorImage.naturalWidth
                    );
        
                currentEditImage.marker_py =
                    Math.round(
                        yp * markerEditorImage.naturalHeight
                    );
        
                marker.style.left =
                    (relX - 18) + "px";
        
                marker.style.top =
                    relY + "px";
        
            }
        
            document.addEventListener("mousemove", e => {
        
                move(
                    e.clientX,
                    e.clientY
                );
        
            });
        
            document.addEventListener("touchmove", e => {
        
                if (!dragging)
                    return;
        
                const t = e.touches[0];
        
                move(
                    t.clientX,
                    t.clientY
                );
        
            });
        
        }
    
        document.addEventListener("click", async (e) => {

        // -----------------------------
        // Bild löschen
        // -----------------------------
        const deleteBtn = e.target.closest(".delete-image");
    
        if (deleteBtn) {
    
            if (!confirm("Bild wirklich löschen?"))
                return;
    
            const imageId = deleteBtn.dataset.image;
    
            const res = await fetch(
                `/tool-errors/delete_temp_image/${imageId}`,
                {
                    method: "POST"
                }
            );
    
            const data = await res.json();
    
            if (data.success) {
                deleteBtn.closest(".image-card").remove();
            }
    
            return;
        }
    
        // -----------------------------
        // Marker bearbeiten
        // -----------------------------
        const markerBtn = e.target.closest(".edit-marker");

        if (markerBtn) {

            const imageId = markerBtn.dataset.image;

            const res = await fetch(
                `/tool-errors/image/${imageId}`
            );

            const image = await res.json();

            openMarkerEditor(image);

            return;
        }
    
    });
    cancelMarkerBtn?.addEventListener("click", () => {

    markerEditorModal.classList.add("hidden");

    });
    saveMarkerBtn?.addEventListener("click", async () => {

    if (!currentEditImage)
        return;

    const res = await fetch(

        `/tool-errors/image/${currentEditImage.id}/marker`,

        {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                marker_x: currentEditImage.marker_x,
                marker_y: currentEditImage.marker_y,
            
                marker_px: currentEditImage.marker_px,
                marker_py: currentEditImage.marker_py,
            
                description:
                    markerEditorDescription.value
            
            })

        }

    );

    const data = await res.json();

    if (data.success) {

        markerEditorModal.classList.add("hidden");

        location.reload();

    }

});
    });

                          
