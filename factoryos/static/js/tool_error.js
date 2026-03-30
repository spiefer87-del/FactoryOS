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
    // 📸 MULTI IMAGE + MARKER
    // =========================

    const imageInput = document.getElementById("imageInput");
    const container = document.getElementById("imagePreviewContainer");

    let imageIndex = 0;

    if (imageInput && container) {

        imageInput.addEventListener("change", function (e) {

            const files = Array.from(e.target.files);

            files.forEach(file => {

                const reader = new FileReader();

                reader.onload = function (ev) {

                    const wrapper = document.createElement("div");
                    wrapper.classList.add("image-wrapper");

                    const img = document.createElement("img");
                    img.src = ev.target.result;

                    // Hidden Inputs pro Bild
                    const markerX = document.createElement("input");
                    markerX.type = "hidden";
                    markerX.name = `marker_x_${imageIndex}`;

                    const markerY = document.createElement("input");
                    markerY.type = "hidden";
                    markerY.name = `marker_y_${imageIndex}`;

                    let currentMarker = null;

                    // 🎯 Marker setzen (PIXEL)
                    img.addEventListener("click", function (e) {

                        const x = e.offsetX;
                        const y = e.offsetY;

                        markerX.value = Math.round(x);
                        markerY.value = Math.round(y);

                        if (currentMarker) currentMarker.remove();

                        const marker = document.createElement("div");
                        marker.classList.add("marker");

                        marker.style.left = x + "px";
                        marker.style.top = y + "px";

                        wrapper.appendChild(marker);
                        currentMarker = marker;

                        console.log("Marker gesetzt:", x, y);
                    });

                    wrapper.appendChild(img);
                    wrapper.appendChild(markerX);
                    wrapper.appendChild(markerY);

                    container.appendChild(wrapper);

                    imageIndex++;
                };

                reader.readAsDataURL(file);
            });

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