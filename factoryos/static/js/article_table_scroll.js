document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const region = document.querySelector(".article-table-scroll");
    const table = document.getElementById("articles-table");
    const hint = document.getElementById("article-table-scroll-hint");
    if (!region || !table || !hint) return;
    function update() {
        hint.hidden = region.scrollWidth <= region.clientWidth + 1;
    }
    // Column preferences, density, search and pagination can all resize the table.
    if (typeof ResizeObserver !== "undefined") {
        const observer = new ResizeObserver(update);
        observer.observe(region);
        observer.observe(table);
    }
    const picker = document.getElementById("article-column-picker");
    if (picker) {
        picker.addEventListener("change", function () { window.requestAnimationFrame(update); });
        picker.addEventListener("click", function () { window.requestAnimationFrame(update); });
    }
    window.addEventListener("resize", update);
    update();
});
