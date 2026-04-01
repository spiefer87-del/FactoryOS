document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // 🔍 TOOL SEARCH
    // =========================

    const input = document.getElementById("toolSearch");
    const dropdown = document.getElementById("toolDropdown");
    const hiddenInput = document.getElementById("tool_id");
    const form = document.querySelector("form");

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

        document.addEventListener("click", function (e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });

        // 🔥 VALIDATION
        if (form) {
            form.addEventListener("submit", function (e) {
                if (!hiddenInput.value) {
                    e.preventDefault();
                    alert("Bitte Werkzeug auswählen!");
                    input.focus();
                }
            });
        }
    }

    // =========================
    // 📸 IMAGE UPLOAD (EINZELN + STABIL)
    // =========================

    const imageInput = document.getElementById("imageInput");
    const container = document.getElementById("imagePreviewContainer");

    let imageIndex = 0;

    if (imageInput && container) {

        imageInput.addEventListener("change", function (e) {

            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();

            reader.onload = function (ev) {

                // =========================
                // 📦 BLOCK
                // =========================

                const block = document.createElement("div");
                block.classList.add("image-block");

                const wrapper = document.createElement("div");
                wrapper.classList.add("image-wrapper");

                const img = document.createElement("img");
                img.src = ev.target.result;
                img.style.touchAction = "none";

                wrapper.appendChild(img);

                // =========================
                // 📝 TEXT
                // =========================

                const textarea = document.createElement("textarea");
                textarea.name = `image_description_${imageIndex}`;
                textarea.placeholder = "Beschreibung zum Bild...";
                textarea.classList.add("form-control");
                textarea.style.marginTop = "8px";

                // =========================
                // 🎯 MARKER INPUTS
                // =========================

                const markerXPercent = document.createElement("input");
                markerXPercent.type = "hidden";
                markerXPercent.name = `marker_x_${imageIndex}`;

                const markerYPercent = document.createElement("input");
                markerYPercent.type = "hidden";
                markerYPercent.name = `marker_y_${imageIndex}`;

                const markerXPixel = document.createElement("input");
                markerXPixel.type = "hidden";
                markerXPixel.name = `marker_px_${imageIndex}`;

                const markerYPixel = document.createElement("input");
                markerYPixel.type = "hidden";
                markerYPixel.name = `marker_py_${imageIndex}`;

                let currentMarker = null;

                // =========================
                // 🎯 MARKER FUNCTION
                // =========================

                function setMarker(clientX, clientY) {

                    const rect = img.getBoundingClientRect();

                    const xPercent = (clientX - rect.left) / rect.width;
                    const yPercent = (clientY - rect.top) / rect.height;

                    const xPixel = xPercent * img.naturalWidth;
                    const yPixel = yPercent * img.naturalHeight;

                    // speichern
                    markerXPercent.value = xPercent;
                    markerYPercent.value = yPercent;

                    markerXPixel.value = Math.round(xPixel);
                    markerYPixel.value = Math.round(yPixel);

                    // alten Marker löschen
                    if (currentMarker) currentMarker.remove();

                    const marker = document.createElement("div");
                    marker.classList.add("marker");

                    marker.style.left = (xPercent * 100) + "%";
                    marker.style.top = (yPercent * 100) + "%";

                    wrapper.appendChild(marker);
                    currentMarker = marker;
                }

                // 🖱️ CLICK
                img.addEventListener("click", function (e) {
                    setMarker(e.clientX, e.clientY);
                });

                // 📱 TOUCH (sauber!)
                img.addEventListener("touchstart", function (e) {
                    e.preventDefault();

                    const touch = e.touches[0];
                    setMarker(touch.clientX, touch.clientY);
                });

                // =========================
                // ❌ REMOVE BUTTON
                // =========================

                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.textContent = "Entfernen";
                removeBtn.classList.add("btn-secondary");
                removeBtn.style.marginTop = "5px";

                removeBtn.onclick = () => {
                    block.remove();
                };

                // =========================
                // 📦 ZUSAMMENBAUEN
                // =========================

                block.appendChild(wrapper);
                block.appendChild(textarea);
                block.appendChild(markerXPercent);
                block.appendChild(markerYPercent);
                block.appendChild(markerXPixel);
                block.appendChild(markerYPixel);
                block.appendChild(removeBtn);

                container.appendChild(block);

                imageIndex++;

                // 🔥 Reset → gleiche Datei erneut möglich
                imageInput.value = "";
            };

            reader.readAsDataURL(file);
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
