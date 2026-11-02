document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const article = document.getElementById("order-article");
    const cycle = document.getElementById("cycle_time_s");
    const list = document.getElementById("order-articles");
    const hint = document.getElementById("order-cycle-hint");
    if (!article || !cycle || !list || !hint) return;
    let manual = cycle.value !== "";
    let automatic = "";
    cycle.addEventListener("input", function () { manual = true; });
    function suggest() {
        const option = Array.from(list.options).find(item => item.value === article.value.trim());
        const value = option ? option.dataset.cycle : "";
        if (!manual && (!cycle.value || cycle.value === automatic)) {
            cycle.value = value && Number.isFinite(Number(value)) && Number(value) > 0 ? value : "";
            automatic = cycle.value;
        }
        hint.textContent = value && Number.isFinite(Number(value)) && Number(value) > 0
            ? "Artikel-Sollwert: " + value + " s. Auftragswert bitte prüfen; manuelle Angaben bleiben erhalten."
            : "Kein gültiger Artikel-Sollwert hinterlegt. Soll-Zykluszeit bitte angeben.";
    }
    article.addEventListener("change", suggest);
    suggest();
});
