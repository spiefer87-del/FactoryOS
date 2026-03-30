document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // 🔍 TOOL SEARCH
    // =========================

    const input = document.getElementById("toolSearch");
    const dropdown = document.getElementById("toolDropdown");
    const hiddenInput = document.getElementById("tool_id");

    let timeout = null;

    if (input && dropdown && hiddenInput) {

        input.addEventListener("input", function () {

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
                                input.value = tool.text;
                                hiddenInput.value = tool.id;
                                dropdown.innerHTML = "";
                                dropdown.style.display = "none";
                            };

                            dropdown.appendChild(div);
                        });

                    })
                    .catch(err => console.error("SEARCH ERROR:", err));

            }, 300);
        });

        // Klick außerhalb → Dropdown schließen
        document.addEventListener("click", function (e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });
    }

    // =========================
    // 📸 IMAGE PREVIEW + MARKER
    // =========================

    const imageInput = document.getElementById("imageInput");
    const preview = document.getElementById("previewImage");

    const markerX = document.getElementById("marker_x");
    const markerY = document.getElementById("marker_y");

    let currentMarker = null;

    if (imageInput && preview) {

        // 📸 Bild laden
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

        // 🎯 Marker setzen (PIXEL – wie QM Builder)
        preview.addEventListener("click", function (e) {

            const container = preview.parentElement;
            const rect = container.getBoundingClientRect();

            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // speichern (Pixel!)
            markerX.value = Math.round(x);
            markerY.value = Math.round(y);

            // alten Marker entfernen
            if (currentMarker) currentMarker.remove();

            const marker = document.createElement("div");
            marker.classList.add("marker");

            marker.style.left = x + "px";
            marker.style.top = y + "px";

            container.appendChild(marker);

            currentMarker = marker;

            console.log("Marker gesetzt:", x, y);
        });
    }

    // =========================
    // 🧾 PRESET → INPUT
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
