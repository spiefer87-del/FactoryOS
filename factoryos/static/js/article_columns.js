document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    const table = document.getElementById("articles-table");
    if (!table) return;
    const prefs = window.FactoryOSPreferences;
    const toggles = Array.from(document.querySelectorAll("[data-article-column-toggle]"));
    const cells = Array.from(table.querySelectorAll("[data-article-column]"));
    const count = document.getElementById("article-visible-count");
    const status = document.getElementById("article-view-status");
    const picker = document.getElementById("article-column-picker");
    const visibility = prefs ? prefs.get("articles.columns") : Object.fromEntries(toggles.map(t => [t.dataset.articleColumnToggle,true]));
    let sequence = 0;
    const unsaved = {};
    function apply() {
        visibility.article_no = true;
        cells.forEach(cell => cell.classList.toggle("article-column-hidden", !visibility[cell.dataset.articleColumn]));
        toggles.forEach(input => { input.checked = visibility[input.dataset.articleColumnToggle]; });
        count.textContent = Object.values(visibility).filter(Boolean).length + "/" + toggles.length;
    }
    function save(patch) {
        Object.assign(unsaved, patch);
        const pending = {...unsaved};
        const current = ++sequence; apply();
        if (!prefs) { status.textContent = "Nicht gespeichert. Bitte Seite neu laden."; return; }
        status.textContent = "Wird im Benutzerkonto gespeichert …";
        prefs.save("articles.columns",pending).then(function () {
            Object.entries(pending).forEach(([key,value])=>{if(unsaved[key]===value)delete unsaved[key];});
            if (current === sequence) status.textContent = "Spaltenauswahl im Benutzerkonto gespeichert.";
        }).catch(function (error) {
            if (current === sequence) status.textContent = "Nicht gespeichert: " + error.message + " Bitte erneut auswählen.";
        });
    }
    toggles.forEach(input => input.addEventListener("change", function () {
        const key=input.dataset.articleColumnToggle;
        if (key!=="article_no") visibility[key]=input.checked;
        save({[key]:visibility[key]});
    }));
    document.getElementById("article-columns-reset").addEventListener("click",function () {
        Object.keys(visibility).forEach(key=>{visibility[key]=true;});save({...visibility});
    });
    picker.addEventListener("keydown",function(event){if(event.key==="Escape"){picker.open=false;picker.querySelector("summary").focus();}});
    status.textContent = prefs ? "Spaltenauswahl aus deinem Benutzerkonto geladen." : "Kontoeinstellungen nicht geladen. Bitte neu laden.";
    apply();
    // Migrate only the former, explicitly per-user article key; never a shared browser key.
    if (prefs && !prefs.has("articles.columns")) {
        try {
            const legacy=JSON.parse(window.localStorage.getItem("factoryos.articles.columns.v1.user."+prefs.userId)||"null");
            if (legacy && typeof legacy==="object" && !Array.isArray(legacy)) {
                const patch={};
                Object.keys(visibility).forEach(key=>{if(key!=="article_no" && typeof legacy[key]==="boolean"){patch[key]=legacy[key];visibility[key]=legacy[key];}});
                if(Object.keys(patch).length) save(patch);
            }
        } catch (_) { /* Server defaults remain usable without local storage. */ }
    }
});
