document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const table = document.getElementById("articles-table");
    if (!table) return;
    const toggles = Array.from(document.querySelectorAll("[data-article-column-toggle]"));
    const cells = Array.from(table.querySelectorAll("[data-article-column]"));
    const count = document.getElementById("article-visible-count");
    const status = document.getElementById("article-view-status");
    const reset = document.getElementById("article-columns-reset");
    const picker = document.getElementById("article-column-picker");
    const storageKey = "factoryos.articles.columns.v1.user." + table.dataset.columnUser;
    const visibility = Object.fromEntries(toggles.map(input => [input.dataset.articleColumnToggle, true]));
    let canStore = true;
    try {
        const saved = JSON.parse(window.localStorage.getItem(storageKey) || "null");
        if (saved && typeof saved === "object" && !Array.isArray(saved)) {
            Object.keys(visibility).forEach(key => {
                if (key !== "article_no" && typeof saved[key] === "boolean") visibility[key] = saved[key];
            });
        }
    } catch (_) { canStore = false; }
    function apply() {
        visibility.article_no = true;
        cells.forEach(cell => cell.classList.toggle("article-column-hidden", !visibility[cell.dataset.articleColumn]));
        toggles.forEach(input => { input.checked = visibility[input.dataset.articleColumnToggle]; });
        count.textContent = Object.values(visibility).filter(Boolean).length + "/" + toggles.length;
        status.textContent = canStore ? "Deine Spaltenauswahl wird in diesem Browser gespeichert." : "Spaltenauswahl gilt aktuell. Die Browserspeicherung ist nicht verfügbar.";
    }
    function save() {
        try {
            window.localStorage.setItem(storageKey, JSON.stringify(visibility));
            canStore = true;
        } catch (_) { canStore = false; }
        apply();
    }
    toggles.forEach(input => input.addEventListener("change", function () {
        const key = input.dataset.articleColumnToggle;
        if (key !== "article_no") visibility[key] = input.checked;
        save();
    }));
    reset.addEventListener("click", function () {
        Object.keys(visibility).forEach(key => { visibility[key] = true; });
        save();
    });
    picker.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            picker.open = false;
            picker.querySelector("summary").focus();
        }
    });
    apply();
});
