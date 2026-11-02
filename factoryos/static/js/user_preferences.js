(function () {
    "use strict";
    const source = document.getElementById("factoryos-preferences-data");
    if (!source) return;
    const boot = JSON.parse(source.textContent);
    if (!boot) return;
    const queues = new Map();
    function copy(value) { return JSON.parse(JSON.stringify(value)); }
    window.FactoryOSPreferences = {
        userId: boot.user_id,
        get(section) { return copy(boot.sections[section].values); },
        has(section) { return boot.sections[section].version > 0; },
        save(section, patch) {
            const values = copy(patch);
            const task = (queues.get(section) || Promise.resolve()).then(async function () {
                for (let attempt = 0; attempt < 2; attempt++) {
                    const response = await window.fetch(boot.url.replace("SECTION", encodeURIComponent(section)), {
                        method: "PATCH", credentials: "same-origin",
                        headers: {"Content-Type": "application/json", "X-CSRF-Token": boot.csrf, "X-FactoryOS-User": String(boot.user_id)},
                        body: JSON.stringify({values, version: boot.sections[section].version}),
                    });
                    const result = await response.json();
                    if (response.status === 409 && result.current) {
                        boot.sections[section] = result.current;
                        continue;
                    }
                    if (!response.ok) throw new Error(result.error || "Speichern fehlgeschlagen.");
                    boot.sections[section] = result;
                    return copy(result.values);
                }
                throw new Error("Parallel geändert. Bitte neu laden und Auswahl prüfen.");
            });
            queues.set(section, task.catch(function () {}));
            return task;
        },
    };
})();
