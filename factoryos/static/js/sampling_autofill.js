document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const source = document.getElementById("sampling-autofill-data");
    if (!source) return;
    const payload = JSON.parse(source.textContent);
    const catalog = payload.catalog;
    const article = document.getElementById("article_id");
    const material = document.getElementById("material_id");
    const tool = document.getElementById("tool_id");
    const reason = document.getElementById("reason");
    const confirmMaterial = document.getElementById("material_confirmed");
    const warning = document.getElementById("sampling-material-warning");
    const materialGroup = document.getElementById("group-material_id");
    const referenceBox = document.getElementById("sampling-reference-values");
    const message = document.getElementById("sampling-autofill-message");
    const touched = new Set();
    const autoValues = new Map();
    let applying = false;
    let lastArticle = article.value;
    const colorKeys = ["masterbatch_id", "color", "masterbatch_percent", "ral_color"];
    const confirmColor = document.getElementById("color_confirmed");
    const colorWarning = document.getElementById("sampling-color-warning");
    function resetColorConfirmation() {
        if (confirmColor) confirmColor.checked = false;
    }
    function updateColorWarning() {
        if (!colorWarning || !confirmColor) return;
        const attention = reason.value === "color_change";
        colorWarning.hidden = !attention;
        confirmColor.required = attention && colorKeys.some(id => document.getElementById(id)?.value !== "" && document.getElementById(id)?.value != null);
        colorKeys.forEach(id => document.getElementById("group-" + id)?.classList.toggle("sampling-material-attention", attention));
    }
    colorKeys.forEach(function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        ["input", "change"].forEach(event => el.addEventListener(event, function () {
            if (!applying) resetColorConfirmation();
            updateColorWarning();
        }));
    });

    ["customer_id", "tool_id", "material_id", ...colorKeys].forEach(function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        ["change", "input"].forEach(function (event) {
            el.addEventListener(event, function () {
                if (!applying) { touched.add(id); autoValues.delete(id); }
            });
        });
    });

    function setSuggestion(id, value) {
        const el = document.getElementById(id);
        value = value == null ? "" : String(value);
        if (!el || touched.has(id)) return;
        // Never replace values loaded from an existing/saved form or a manual entry.
        if (el.value && !autoValues.has(id)) return;
        applying = true;
        if (el.tomselect) el.tomselect.setValue(value, true);
        else el.value = value;
        autoValues.set(id, value);
        applying = false;
    }

    function updateReferences() {
        updateColorWarning();
        const a = catalog.articles[article.value];
        const t = catalog.tools[tool.value];
        const m = catalog.materials[material.value];
        const useSaved = payload.saved &&
            article.value === payload.ids.article_id &&
            tool.value === payload.ids.tool_id &&
            material.value === payload.ids.material_id;
        const refs = useSaved ? payload.saved : Object.assign({}, a ? a.reference : {},
            t ? t.reference : {}, m ? m.reference : {});
        referenceBox.replaceChildren();
        Object.entries(refs).forEach(function (pair) {
            const row = document.createElement("div");
            const label = document.createElement("dt");
            const value = document.createElement("dd");
            label.textContent = pair[0];
            value.textContent = pair[1] == null || pair[1] === "" ? "-" : String(pair[1]);
            row.append(label, value);
            referenceBox.append(row);
        });
        warning.hidden = reason.value !== "material_change";
        materialGroup.classList.toggle("sampling-material-attention", !warning.hidden);
        confirmMaterial.required = !warning.hidden && !!material.value;
        document.getElementById("sampling-stock-material").textContent =
            a && a.material_id && material.options.length
                ? (Array.from(material.options).find(o => o.value === a.material_id)?.textContent || "Kein Rohstoff hinterlegt")
                : "Kein Rohstoff am Artikel hinterlegt";
    }

    function materialSuggestions() {
        const a = catalog.articles[article.value];
        const m = catalog.materials[material.value];
        colorKeys.forEach(function (id) {
            const batchId = document.getElementById("masterbatch_id")?.value;
            const batch = catalog.materials[batchId];
            let value = a?.[id];
            if (id === "color") value = batchId ? (batch?.color || "") : (m?.color || "");
            if (id === "ral_color") value = batch?.ral_color || "";
            if (id === "masterbatch_percent" && batchId !== a?.masterbatch_id) value = "";
            setSuggestion(id, reason.value === "color_change" ? "" : value);
        });
        updateReferences();
    }

    article.addEventListener("change", function () {
        if (article.value === lastArticle) return;
        lastArticle = article.value;
        resetColorConfirmation();
        confirmMaterial.checked = false;
        const a = catalog.articles[article.value];
        setSuggestion("customer_id", a ? a.customer_id : "");
        setSuggestion("material_id", a ? a.material_id : "");
        setSuggestion("tool_id", a ? a.tool_id : "");
        message.textContent = a && a.tool_count > 1
            ? "Mehrere Werkzeuge zugeordnet (" + a.tool_names.join(", ") + "). Bitte Werkzeug bewusst auswählen. Manuelle Angaben bleiben erhalten."
            : "Verfügbare, eindeutige Zuordnungen wurden vorgeschlagen. Manuelle Angaben bleiben erhalten.";
        materialSuggestions();
    });
    material.addEventListener("change", function () {
        resetColorConfirmation();
        confirmMaterial.checked = false;
        materialSuggestions();
    });
    tool.addEventListener("change", updateReferences);
    const batch = document.getElementById("masterbatch_id");
    if (batch) batch.addEventListener("change", function () {
        resetColorConfirmation();
        const b = catalog.materials[batch.value];
        setSuggestion("color", b?.color || "");
        setSuggestion("ral_color", b?.ral_color || "");
        const a = catalog.articles[article.value];
        setSuggestion("masterbatch_percent", batch.value === a?.masterbatch_id ? a.masterbatch_percent : "");
        updateReferences();
    });
    reason.addEventListener("change", function () {
        resetColorConfirmation();
        confirmMaterial.checked = false;
        materialSuggestions();
    });
    // Initial rendering only: never apply fresh defaults to an existing or failed form.
    updateReferences();
});

