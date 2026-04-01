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
    // 📸 IMAGE UPLOAD (FIXED CLEAN)
    // =========================
    
    const imageInput = document.getElementById("imageInput");
    const container = document.getElementById("imagePreviewContainer");
    
    if (imageInput && container) {

        imageInput.addEventListener("change", function (e) {
    
            const files = Array.from(e.target.files);
    
            files.forEach((file) => {
    
                const reader = new FileReader();
    
                reader.onload = function (ev) {
    
                    const block = document.createElement("div");
                    block.classList.add("image-block");
    
                    const wrapper = document.createElement("div");
                    wrapper.classList.add("image-wrapper");
                    wrapper.style.position = "relative";
    
                    const img = document.createElement("img");
                    img.src = ev.target.result;
                    img.style.width = "100%";
    
                    wrapper.appendChild(img);
    
                    const textarea = document.createElement("textarea");
                    textarea.name = "image_description[]";
    
                    const markerX = document.createElement("input");
                    markerX.type = "hidden";
                    markerX.name = "marker_x[]";
    
                    const markerY = document.createElement("input");
                    markerY.type = "hidden";
                    markerY.name = "marker_y[]";
    
                    let currentMarker = null;
    
                    function setMarker(x, y) {
                        const rect = img.getBoundingClientRect();
    
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
    
                    img.addEventListener("click", (e) => {
                        setMarker(e.clientX, e.clientY);
                    });
    
                    img.addEventListener("touchstart", (e) => {
                        e.preventDefault();
                        const t = e.touches[0];
                        setMarker(t.clientX, t.clientY);
                    });
    
                    block.appendChild(wrapper);
                    block.appendChild(textarea);
                    block.appendChild(markerX);
                    block.appendChild(markerY);
    
                    container.appendChild(block);
                };
    
                reader.readAsDataURL(file);
            });
    
            // ❌ NICHT resetten!
            // imageInput.value = "";
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
