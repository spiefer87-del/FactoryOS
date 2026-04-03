document.addEventListener("DOMContentLoaded", function () {

    console.log("✅ tool_error.js geladen");


    // =========================
    // 🔥 TOMSELECT KILL
    // =========================

    const toolInput = document.getElementById("toolSearch");

    if (toolInput && toolInput.tomselect) {
        toolInput.tomselect.destroy();
        console.log("🔥 TomSelect deaktiviert");
    }


    // =========================
    // 🔥 TEMP ID
    // =========================

    function generateTempId() {
        return 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    const tempInput = document.getElementById("temp_id");
    if (tempInput) {
        tempInput.value = generateTempId();
    }


    // =========================
    // 🔍 TOOL SEARCH
    // =========================

    const dropdown = document.getElementById("toolDropdown");
    const hiddenInput = document.getElementById("tool_id");
    const form = document.querySelector("form");

    let timeout = null;
    let currentFocus = -1;
    let currentResults = [];

    if (toolInput && dropdown && hiddenInput) {

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


        function selectTool(index) {
            const tool = currentResults[index];
            if (!tool) return;

            toolInput.value = tool.text;
            hiddenInput.value = tool.id;

            dropdown.style.display = "none";
        }


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


        document.addEventListener("click", function (e) {
            if (!toolInput.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });


        if (form) {
            form.addEventListener("submit", async function (e) {

                if (hiddenInput.value) return;

                e.preventDefault();

                const query = toolInput.value;

                if (!query) {
                    alert("Bitte Werkzeug eingeben!");
                    return;
                }

                try {
                    const res = await fetch(`/masterdata/tools/api/search?q=${query}`);
                    const data = await res.json();

                    if (!data.results || data.results.length === 0) {
                        alert("Werkzeug nicht gefunden!");
                        return;
                    }

                    hiddenInput.value = data.results[0].id;
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

    if (imageInput && preview && wrapper) {

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


        if (uploadBtn) {
            uploadBtn.addEventListener("click", function () {

                const file = imageInput.files[0];

                if (!file || !markerX.value || !markerY.value) {
                    alert("Bild + Marker erforderlich");
                    return;
                }

                const formData = new FormData();

                formData.append("image", file);
                formData.append("marker_x", markerX.value);
                formData.append("marker_y", markerY.value);
                formData.append("description", textarea.value);
                formData.append("temp_id", tempInput?.value);

                fetch("/tool-errors/upload_temp_image", {
                    method: "POST",
                    body: formData
                });
            });
        }
    }


    // =========================
    // 🧠 STATUS MODAL (WICHTIG!)
    // =========================

    const modal = document.getElementById("toolStatusModal");

    if (modal) {

        const urlParams = new URLSearchParams(window.location.search);

        if (urlParams.get("new") === "1") {

            console.log("🔥 Modal wird angezeigt");

            modal.classList.remove("hidden");

            const errorId = window.location.pathname.split("/").pop();

            const defectBtn = document.getElementById("setDefect");
            const activeBtn = document.getElementById("keepActive");

            if (defectBtn) {
                defectBtn.onclick = () => updateStatus(errorId, "defekt");
            }

            if (activeBtn) {
                activeBtn.onclick = () => updateStatus(errorId, "aktiv");
            }
        }
    }


    function updateStatus(errorId, status) {

        console.log("📡 Status update:", errorId, status);

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