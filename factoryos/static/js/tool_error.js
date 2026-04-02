document.addEventListener("DOMContentLoaded", function () {

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
    // 🔍 TOOL SEARCH
    // =========================

    const toolInput = document.getElementById("toolSearch");
    const dropdown = document.getElementById("toolDropdown");
    const hiddenInput = document.getElementById("tool_id");
    const form = document.querySelector("form");

    let timeout = null;

    if (toolInput && dropdown && hiddenInput) {

        toolInput.addEventListener("input", function () {

            clearTimeout(timeout);

            const query = this.value;
            hiddenInput.value = "";

            if (query.length < 2) {
                dropdown.style.display = "none";
                dropdown.innerHTML = "";
                return;
            }

            timeout = setTimeout(() => {

                fetch(`/masterdata/tools/api/search?q=${query}`)
                    .then(res => res.json())
                    .then(data => {

                        dropdown.innerHTML = "";

                        if (!data.results || data.results.length === 0) {
                            dropdown.style.display = "none";
                            return;
                        }

                        dropdown.style.display = "block";

                        data.results.forEach(tool => {

                            const div = document.createElement("div");
                            div.classList.add("dropdown-item");
                            div.textContent = tool.text;

                            div.onclick = () => {
                                toolInput.value = tool.text;
                                hiddenInput.value = tool.id;
                                dropdown.innerHTML = "";
                                dropdown.style.display = "none";
                            };

                            dropdown.appendChild(div);
                        });

                    });

            }, 300);
        });

        document.addEventListener("click", function (e) {
            if (!toolInput.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });

        if (form) {
            form.addEventListener("submit", function (e) {
                if (!hiddenInput.value) {
                    e.preventDefault();
                    alert("Bitte Werkzeug auswählen!");
                    toolInput.focus();
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

    function setMarker(x, y) {

        const rect = preview.getBoundingClientRect();

        const xp = (x - rect.left) / rect.width;
        const yp = (y - rect.top) / rect.height;

        markerX.value = xp;
        markerY.value = yp;

        if (currentMarker) currentMarker.remove();

        const marker = document.createElement("div");
        marker.classList.add("marker");

        marker.style.left = (xp * 100) + "%";
        marker.style.top = (yp * 100) + "%";

        wrapper.appendChild(marker);
        currentMarker = marker;
    }

    preview.addEventListener("click", (e) => {
        setMarker(e.clientX, e.clientY);
    });

    preview.addEventListener("touchstart", (e) => {
        e.preventDefault();
        const t = e.touches[0];
        setMarker(t.clientX, t.clientY);
    });


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

            if (!markerX.value || !markerY.value) {
                alert("Bitte Marker setzen");
                return;
            }

            const formData = new FormData();

            formData.append("image", file);
            formData.append("marker_x", markerX.value);
            formData.append("marker_y", markerY.value);
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

                addToGallery(preview.src, markerX.value, markerY.value, textarea.value);

                // RESET
                preview.style.display = "none";
                imageInput.value = "";
                textarea.value = "";
                markerX.value = "";
                markerY.value = "";

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

    function addToGallery(src, x, y, text) {

    const wrap = document.createElement("div");
    wrap.classList.add("image-wrapper");

    const img = document.createElement("img");
    img.src = src;

    wrap.appendChild(img);

    const marker = document.createElement("div");
    marker.classList.add("marker");

    marker.style.left = (x * 100) + "%";
    marker.style.top = (y * 100) + "%";

    wrap.appendChild(marker);

    if (text) {
        const desc = document.createElement("div");
        desc.classList.add("image-description");
        desc.innerText = text;
        wrap.appendChild(desc);
    }

    gallery.appendChild(wrap);

    // 🔥 SCROLL zum Upload Bereich (nicht verschieben!)
    const uploadBox = document.getElementById("uploadBox");

    uploadBox.scrollIntoView({
        behavior: "smooth",
        block: "center"
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

});

