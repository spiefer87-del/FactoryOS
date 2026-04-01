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
    // 📸 IMAGE UPLOAD (STABLE FIX)
    // =========================

    const imageInput = document.getElementById("imageInput");
    const container = document.getElementById("imagePreviewContainer");

    function generateId() {
        return crypto.randomUUID();
    }

    if (imageInput && container) {

        imageInput.addEventListener("change", function (e) {

            const file = e.target.files[0];
            if (!file) return;

            const id = generateId();

            const reader = new FileReader();

            reader.onload = function (ev) {

                // 📦 BLOCK
                const block = document.createElement("div");
                block.classList.add("image-block");

                const wrapper = document.createElement("div");
                wrapper.classList.add("image-wrapper");

                const img = document.createElement("img");
                img.src = ev.target.result;
                img.style.width = "100%";
                img.style.display = "block";
                img.style.touchAction = "none";

                wrapper.appendChild(img);

                // 📁 FILE (OHNE DataTransfer!)
                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.name = "images";
                fileInput.style.display = "none";

                // 🔥 DIREKT FILE ZUWEISEN (funktioniert stabiler)
                const dataTransfer = new ClipboardEvent('').clipboardData || new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;

                // 🧾 ID
                const idInput = document.createElement("input");
                idInput.type = "hidden";
                idInput.name = "image_ids";
                idInput.value = id;

                // 📝 TEXT
                const textarea = document.createElement("textarea");
                textarea.name = `description_${id}`;
                textarea.placeholder = "Beschreibung...";
                textarea.classList.add("form-control");

                // 🎯 MARKER
                const markerX = document.createElement("input");
                markerX.type = "hidden";
                markerX.name = `marker_x_${id}`;

                const markerY = document.createElement("input");
                markerY.type = "hidden";
                markerY.name = `marker_y_${id}`;

                let currentMarker = null;

                function setMarker(clientX, clientY) {

                    const rect = img.getBoundingClientRect();

                    const xPercent = (clientX - rect.left) / rect.width;
                    const yPercent = (clientY - rect.top) / rect.height;

                    markerX.value = xPercent;
                    markerY.value = yPercent;

                    if (currentMarker) currentMarker.remove();

                    const marker = document.createElement("div");
                    marker.classList.add("marker");

                    marker.style.left = (xPercent * 100) + "%";
                    marker.style.top = (yPercent * 100) + "%";

                    wrapper.appendChild(marker);
                    currentMarker = marker;
                }

                // 🖱 CLICK
                img.addEventListener("click", function (e) {
                    setMarker(e.clientX, e.clientY);
                });

                // 📱 TOUCH
                img.addEventListener("touchstart", function (e) {
                    e.preventDefault();
                    const t = e.touches[0];
                    setMarker(t.clientX, t.clientY);
                });

                // ❌ REMOVE
                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.textContent = "Entfernen";
                removeBtn.classList.add("btn-secondary");
                removeBtn.onclick = () => block.remove();

                // 📦 BUILD
                block.appendChild(wrapper);
                block.appendChild(textarea);
                block.appendChild(markerX);
                block.appendChild(markerY);
                block.appendChild(fileInput);
                block.appendChild(idInput);
                block.appendChild(removeBtn);

                container.appendChild(block);

                // wichtig
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
