document.addEventListener("DOMContentLoaded", function () {
// =========================
// 🔧 TOOL SEARCH
// =========================

const input = document.getElementById("toolSearch");
const dropdown = document.getElementById("toolDropdown");
const hiddenInput = document.getElementById("tool_id");

let timeout = null;

if (input) {
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

                    if (data.results.length === 0) {
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
}

// =========================
// 🔧 ERROR PRESETS
// =========================

const presetSelect = document.getElementById("errorPreset");
const errorInput = document.getElementById("error_type");

if (presetSelect) {
    presetSelect.addEventListener("change", function () {
        if (this.value) {
            errorInput.value = this.value;
        }
    });
}

// =========================
// 📸 IMAGE PREVIEW + MARKER
// =========================

const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("previewImage");

const markerX = document.getElementById
});
