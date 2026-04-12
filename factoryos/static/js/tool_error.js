// 🔥 KILL TOMSELECT falls aktiv
document.addEventListener("DOMContentLoaded", function () {

    const toolInput = document.getElementById("toolSearch");

    if (toolInput && toolInput.tomselect) {
        toolInput.tomselect.destroy();
        console.log("🔥 TomSelect deaktiviert für toolSearch");
    }


    // =========================
    // 🔥 TEMP ID FIX (WICHTIG!)
    // =========================
    function generateTempId() {
        return 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    const TEMP_ID = generateTempId();

    const tempInput = document.getElementById("temp_id");
    if (tempInput) tempInput.value = TEMP_ID;


    // =========================
    // 🔍 PERFECT TOOL SEARCH
    // =========================
    
    const dropdown = document.getElementById("toolDropdown");
    const hiddenInput = document.getElementById("tool_id");
    const form = document.querySelector("form");
    
    let timeout = null;
    let currentFocus = -1;
    let currentResults = [];
    
    if (toolInput && dropdown && hiddenInput) {
    
        // 🔍 LIVE SEARCH
        toolInput.addEventListener("input", function () {
    
            clearTimeout(timeout);
            const query = this.value;
            hiddenInput.value = "";
    
            if (query.length < 2) {
                dropdown.style.display = "none";
                return;
            }
    
            timeout = setTimeout(async () => {
    
                try {
                    const res = await fetch(`/masterdata/tools/api/search?q=${query}`);
                    const data = await res.json();
    
                    dropdown.innerHTML = "";
                    currentResults = data.results || [];
                    currentFocus = -1;
    
                    if (currentResults.length === 0) {
                        dropdown.style.display = "none";
                        return;
                    }
    
                    dropdown.style.display = "block";
    
                    currentResults.forEach((tool, index) => {
    
                        const div = document.createElement("div");
                        div.classList.add("dropdown-item");
                        div.textContent = tool.text;
    
                        div.onclick = () => selectTool(index);
    
                        dropdown.appendChild(div);
                    });
    
                } catch (err) {
                    console.error("Search error:", err);
                }
    
            }, 250);
        });
    
    
        // 🎯 SELECT FUNCTION
        function selectTool(index) {
            const tool = currentResults[index];
            if (!tool) return;
    
            toolInput.value = tool.text;
            hiddenInput.value = tool.id;
    
            dropdown.style.display = "none";

            // 🔥 Status setzen
            const statusSelect = document.getElementById("tool_status");
            if (statusSelect && tool.status) {
                statusSelect.value = tool.status;
            }
        }
    
    
        // ⌨️ KEYBOARD NAVIGATION
        toolInput.addEventListener("keydown", function (e) {
    
            const items = dropdown.querySelectorAll(".dropdown-item");
    
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
    
                if (currentFocus > -1 && items[currentFocus]) {
                    e.preventDefault();
                    items[currentFocus].click();
                } else if (currentResults.length > 0) {
                    e.preventDefault();
                    selectTool(0);
                }
            }
        });
    
    
        function setActive(items) {
            if (!items.length) return;
    
            items.forEach(item => item.classList.remove("active"));
    
            if (currentFocus >= items.length) currentFocus = 0;
            if (currentFocus < 0) currentFocus = items.length - 1;
    
            items[currentFocus].classList.add("active");
        }
    
    
        // 🖱 CLICK OUTSIDE
        document.addEventListener("click", function (e) {
            if (!toolInput.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });
    
    
        // 🧠 SMART SUBMIT (kein nerviges Alert mehr)
        if (form) {
            form.addEventListener("submit", async function (e) {

                console.log("🚀 Submit gestartet");
            
                // Wenn ID schon da → passt
                if (hiddenInput.value) {
                    console.log("✅ Tool ID vorhanden:", hiddenInput.value);
                    return;
                }
            
                e.preventDefault();
            
                const query = toolInput.value;
            
                if (!query) {
                    alert("Bitte Werkzeug eingeben!");
                    return;
                }
            
                try {
                    const res = await fetch(`/masterdata/tools/api/search?q=${query}`);
                    const data = await res.json();
            
                    console.log("🔍 API Antwort:", data);
            
                    if (!data.results || data.results.length === 0) {
                        alert("Werkzeug nicht gefunden!");
                        return;
                    }
            
                    // 🔥 IMMER ersten Treffer nehmen
                    const tool = data.results[0];
            
                    hiddenInput.value = tool.id;
            
                    console.log("✅ Tool automatisch gesetzt:", tool.id);
            
                    form.submit();
            
                } catch (err) {
                    console.error("❌ Fehler:", err);
                }
            });
        }
    }


    // =========================
    // 📸 IMAGE MODULE
    // =========================

    const imageInput = document.getElementById("imageInput");
    const preview = document.getElementById("previewImage");
    const wrapper = document.getElementById("previewWrapper");

    const markerX = document.getElementById("marker_x");
    const markerY = document.getElementById("marker_y");

    const uploadBtn = document.getElementById("uploadBtn");
    const textarea = document.getElementById("imageDescription");
    const gallery = document.getElementById("imageGallery");

    let currentMarker = null;

    if (!imageInput || !preview || !wrapper) {
        console.error("❌ Image Module Elemente fehlen!");
        return;
    }

    // =========================
    // 📸 PREVIEW
    // =========================

    imageInput.addEventListener("change", function (e) {

        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();

        reader.onload = function (ev) {
            preview.src = ev.target.result;
            preview.style.display = "block";
        };

        reader.readAsDataURL(file);
    });


    // =========================
    // 🎯 MARKER
    // =========================
    let markerCount = 0;

    function setMarker(x, y) {

        const rect = preview.getBoundingClientRect();

        const relX = x - rect.left;
        const relY = y - rect.top;

        const xp = relX / rect.width;
        const yp = relY / rect.height;

        const naturalWidth = preview.naturalWidth;
        const naturalHeight = preview.naturalHeight;

        const px = xp * naturalWidth;
        const py = yp * naturalHeight;

        markerX.value = xp;
        markerY.value = yp;

        document.getElementById("marker_px").value = Math.round(px);
        document.getElementById("marker_py").value = Math.round(py);

        if (currentMarker) currentMarker.remove();

        const marker = document.createElement("div");
        marker.classList.add("marker-advanced");

        marker.innerHTML = `
            <div class="marker-circle">1</div>
            <div class="marker-arrow"></div>
        `;

        // Spitze exakt auf Klickpunkt
        marker.style.left = (relX - 34) + "px";
        marker.style.top  = (relY - 12) + "px";

        wrapper.appendChild(marker);
        currentMarker = marker;

        enableDrag(marker);
    }


    // Desktop
    preview.addEventListener("click", (e) => {
        setMarker(e.clientX, e.clientY);
    });

    // Mobile
    preview.addEventListener("touchstart", (e) => {
        e.preventDefault();
        const t = e.touches[0];
        setMarker(t.clientX, t.clientY);
    });


    function enableDrag(marker) {

        let dragging = false;

        function move(clientX, clientY) {

            const rect = preview.getBoundingClientRect();

            let relX = clientX - rect.left;
            let relY = clientY - rect.top;

            relX = Math.max(0, Math.min(relX, rect.width));
            relY = Math.max(0, Math.min(relY, rect.height));

            const xp = relX / rect.width;
            const yp = relY / rect.height;

            markerX.value = xp;
            markerY.value = yp;

            const px = xp * preview.naturalWidth;
            const py = yp * preview.naturalHeight;

            document.getElementById("marker_px").value = Math.round(px);
            document.getElementById("marker_py").value = Math.round(py);

            marker.style.left = (relX - 34) + "px";
            marker.style.top  = (relY - 12) + "px";
        }

        marker.addEventListener("mousedown", function(e){
            dragging = true;
            e.preventDefault();
        });

        document.addEventListener("mousemove", function(e){
            if (!dragging) return;
            move(e.clientX, e.clientY);
        });

        document.addEventListener("mouseup", function(){
            dragging = false;
        });

        marker.addEventListener("touchstart", function(e){
            dragging = true;
            e.preventDefault();
        });

        document.addEventListener("touchmove", function(e){
            if (!dragging) return;

            const t = e.touches[0];
            move(t.clientX, t.clientY);
        });

        document.addEventListener("touchend", function(){
            dragging = false;
        });
    }
    
    // =========================
    // 🚀 UPLOAD
    // =========================

    if (uploadBtn) {

        uploadBtn.addEventListener("click", function () {

            console.log("🚀 Upload gestartet");

            const file = imageInput.files[0];

            if (!file) {
                alert("Bitte Bild auswählen");
                return;
            }

            if (!markerX.value || !markerY.value || 
                !document.getElementById("marker_px").value) {
                alert("Bitte Marker setzen");
                return;
            }

            const formData = new FormData();

            formData.append("image", file);
            formData.append("marker_x", markerX.value);
            formData.append("marker_y", markerY.value);
            
            // 🔥 NEU
            formData.append("marker_px", document.getElementById("marker_px").value);
            formData.append("marker_py", document.getElementById("marker_py").value);
            
            formData.append("description", textarea.value);
            formData.append("temp_id", TEMP_ID);

            fetch("/tool-errors/upload_temp_image", {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {

                console.log("✅ Server Antwort:", data);

                if (!data.success) {
                    alert("Upload fehlgeschlagen");
                    return;
                }

                addToGallery(preview.src, markerX.value, markerY.value, textarea.value, data.image_id);

                // RESET
                preview.style.display = "none";
                imageInput.value = "";
                textarea.value = "";
                
                markerX.value = "";
                markerY.value = "";
                
                document.getElementById("marker_px").value = "";
                document.getElementById("marker_py").value = "";
                
                // 🔥 Nummer zurücksetzen
                markerCount = 0;
                
                if (currentMarker) currentMarker.remove();
            })
            .catch(err => {
                console.error("❌ Upload Fehler:", err);
            });
        });
    }


    // =========================
    // 📸 GALLERY
    // =========================

    function addToGallery(src, x, y, text, imageId) {

        const wrap = document.createElement("div");
        wrap.classList.add("image-wrapper");
    
        const img = document.createElement("img");
        img.src = src;
    
        wrap.appendChild(img);
    
        // 🎯 Marker
        const marker = document.createElement("div");
        marker.classList.add("marker-advanced");

        marker.style.left = (x * 100) + "%";
        marker.style.top = (y * 100) + "%";

        marker.innerHTML = `
            <div class="marker-circle">1</div>
            <div class="marker-arrow"></div>
        `;
    
        wrap.appendChild(marker);
    
        // 📝 Beschreibung
        if (text) {
            const desc = document.createElement("div");
            desc.classList.add("image-description");
            desc.innerText = text;
            wrap.appendChild(desc);
        }
    
        // ❌ DELETE BUTTON
        const delBtn = document.createElement("button");
        delBtn.innerText = "✕";
        delBtn.classList.add("delete-btn");
        delBtn.type = "button";  // 🔥 WICHTIG!!!
        
        delBtn.onclick = (e) => {
        
            e.preventDefault();  // 🔥 extra safe
        
            if (!confirm("Bild wirklich löschen?")) return;
        
            fetch(`/tool-errors/delete_temp_image/${imageId}`, {
                method: "POST"
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    wrap.remove();
                } else {
                    alert("Löschen fehlgeschlagen");
                }
            });
        };
    
        wrap.appendChild(delBtn);
    
        gallery.appendChild(wrap);


        // nur leicht nach unten scrollen
        uploadBox.scrollIntoView({
            behavior: "smooth",
            block: "end"
        });
        }
    

    // =========================
    // 🧾 PRESET
    // =========================

    const presetSelect = document.getElementById("errorPreset");
    const errorInput = document.getElementById("error_type");

    if (presetSelect && errorInput) {
        presetSelect.addEventListener("change", function () {
            if (this.value) {
                errorInput.value = this.value;
            }
        });
    }

    // =========================
    // Status Update Modal (NEU)
    // =========================

    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.get("new") === "1") {

        const modal = document.getElementById("toolStatusModal");
        modal.classList.remove("hidden");

        const errorId = window.location.pathname.split("/").pop();

        document.getElementById("setDefect").onclick = () => {
            updateStatus(errorId, "defekt");
        };

        document.getElementById("keepActive").onclick = () => {
            updateStatus(errorId, "aktiv");
        };
    }

    function updateStatus(errorId, status) {

        fetch(`/tool-errors/set_tool_status/${errorId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ status })
        })
        .then(res => res.json())
        .then(() => {
            location.reload();
        });
    }

});


