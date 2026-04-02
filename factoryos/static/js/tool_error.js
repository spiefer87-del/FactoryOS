const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("previewImage");
const wrapper = document.getElementById("previewWrapper");

const markerX = document.getElementById("marker_x");
const markerY = document.getElementById("marker_y");

const uploadBtn = document.getElementById("uploadBtn");
const textarea = document.getElementById("imageDescription");

let currentMarker = null;

// 📸 Preview
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

// 🎯 Marker
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

// CLICK
preview.addEventListener("click", (e) => {
    setMarker(e.clientX, e.clientY);
});

// TOUCH
preview.addEventListener("touchstart", (e) => {
    e.preventDefault();
    const t = e.touches[0];
    setMarker(t.clientX, t.clientY);
});

// 🚀 UPLOAD
uploadBtn.addEventListener("click", function () {

    const file = imageInput.files[0];

    if (!file) {
        alert("Bitte Bild auswählen");
        return;
    }

    const formData = new FormData();

    formData.append("image", file);
    formData.append("marker_x", markerX.value);
    formData.append("marker_y", markerY.value);
    formData.append("description", textarea.value);

    fetch(`/tool_error/upload_image/${ERROR_ID}`, {
        method: "POST",
        body: formData
    })
    .then(() => {
        location.reload(); // einfach & stabil
    });
});

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
    
            container.innerHTML = "";
    
            const files = Array.from(e.target.files);
    
            files.forEach((file, index) => {
    
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
    
                    // 📝 TEXT
                    const textarea = document.createElement("textarea");
                    textarea.name = `image_description_${index}`;
    
                    // 🎯 MARKER
                    const markerX = document.createElement("input");
                    markerX.type = "hidden";
                    markerX.name = `marker_x_${index}`;
                    markerX.value = 0;
    
                    const markerY = document.createElement("input");
                    markerY.type = "hidden";
                    markerY.name = `marker_y_${index}`;
                    markerY.value = 0;
    
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
