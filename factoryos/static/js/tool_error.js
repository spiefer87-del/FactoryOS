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

        // VALIDATION
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
    // 📸 IMAGE UPLOAD (FIXED)
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

                const block = document.createElement("div");
                block.classList.add("image-block");

                const wrapper = document.createElement("div");
                wrapper.classList.add("image-wrapper");

                const img = document.createElement("img");
                img.src = ev.target.result;
                img.style.touchAction = "none";

                wrapper.appendChild(img);

                // =========================
                // 🔥 WICHTIG: FILE KLONEN
                // =========================

                const dt = new DataTransfer();
                dt.items.add(file);

                const hiddenFileInput = document.createElement("input");
                hiddenFileInput.type = "file";
                hiddenFileInput.name = "images";
                hiddenFileInput.files = dt.files;
                hiddenFileInput.style.display = "none";

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

                const markerX = document.createElement("input");
                markerX.type = "hidden";
                markerX.name = `marker_x_${imageIndex}`;

                const markerY = document.createElement("input");
                markerY.type = "hidden";
                markerY.name = `marker_y_${imageIndex}`;

                const markerPX = document.createElement("input");
                markerPX.type = "hidden";
                markerPX.name = `marker_px_${imageIndex}`;

                const markerPY = document.createElement("input");
                markerPY.type = "hidden";
                markerPY.name = `marker_py_${imageIndex}`;

                let currentMarker = null;

                function setMarker(clientX, clientY) {

                    const rect = img.getBoundingClientRect();

                    const xPercent = (clientX - rect.left) / rect.width;
                    const yPercent = (clientY - rect.top) / rect.height;

                    const xPixel = xPercent * img.naturalWidth;
                    const yPixel = yPercent * img.naturalHeight;

                    markerX.value = xPercent;
                    markerY.value = yPercent;

                    markerPX.value = Math.round(xPixel);
                    markerPY.value = Math.round(yPixel);

                    if (currentMarker) currentMarker.remove();

                    const marker = document.createElement("div");
                    marker.classList.add("marker");

                    marker.style.left = (xPercent * 100) + "%";
                    marker.style.top = (yPercent * 100) + "%";

                    wrapper.appendChild(marker);
                    currentMarker = marker;
                }

                img.addEventListener("click", (e) => {
                    setMarker(e.clientX, e.clientY);
                });

                img.addEventListener("touchstart", (e) => {
                    e.preventDefault();
                    const touch = e.touches[0];
                    setMarker(touch.clientX, touch.clientY);
                });

                // REMOVE BUTTON
                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.textContent = "Entfernen";
                removeBtn.classList.add("btn-secondary");

                removeBtn.onclick = () => block.remove();

                // =========================
                // BUILD
                // =========================

                block.appendChild(wrapper);
                block.appendChild(textarea);
                block.appendChild(markerX);
                block.appendChild(markerY);
                block.appendChild(markerPX);
                block.appendChild(markerPY);
                block.appendChild(hiddenFileInput);
                block.appendChild(removeBtn);

                container.appendChild(block);

                imageIndex++;

                // 🔥 wichtig: reset
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
