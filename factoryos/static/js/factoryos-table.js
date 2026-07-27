document.addEventListener("DOMContentLoaded", function () {

    const tables = document.querySelectorAll(".fos-table");

    tables.forEach(table => {

        const wrapper = table.closest(".fos-table-wrapper");

        if (!wrapper) {
            return;
        }

        const tbody = table.querySelector("tbody");

        if (!tbody) {
            return;
        }

        const searchInput = wrapper.querySelector(".fos-search");
        const pagination = wrapper.querySelector(".fos-pagination");

        const perPage = 10;

        let allRows = Array.from(tbody.querySelectorAll("tr"));
        let filteredRows = [...allRows];

        let currentPage = 1;
        let sortColumnIndex = null;
        let sortDirection = "asc";


        // =====================================
        // CELL TEXT
        // =====================================

        function getCellText(row, index) {

            const cell = row.children[index];

            if (!cell) {
                return "";
            }

            return cell.innerText
                .replace(/\s+/g, " ")
                .trim()
                .toLowerCase();

        }


        // =====================================
        // VALUE NORMALIZATION
        // =====================================

        function normalizeDate(value) {

            const match = value.match(
                /^(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?/
            );

            if (!match) {
                return null;
            }

            const day = Number(match[1]);
            const month = Number(match[2]) - 1;
            const year = Number(match[3]);
            const hour = match[4] ? Number(match[4]) : 0;
            const minute = match[5] ? Number(match[5]) : 0;

            return new Date(
                year,
                month,
                day,
                hour,
                minute
            ).getTime();

        }


        function normalizeNumber(value) {

            let cleaned = value
                .trim()
                .replace(/\s*(kg|g|mm|cm|m|stück|st\.?|%)$/i, "")
                .trim();
        
            /*
             * Nur Werte behandeln, die vollständig numerisch sind.
             *
             * ATH001, COR063 usw. bleiben dadurch Text und werden
             * über localeCompare natürlich sortiert.
             */
        
            // Deutsche Ganzzahl oder Dezimalzahl: 1234 / 1234,50
            if (/^-?\d+(?:,\d+)?$/.test(cleaned)) {
        
                return Number(
                    cleaned.replace(",", ".")
                );
        
            }
        
            // Deutsche Tausenderdarstellung: 1.234 / 1.234,50
            if (/^-?\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(cleaned)) {
        
                return Number(
                    cleaned
                        .replace(/\./g, "")
                        .replace(",", ".")
                );
        
            }
        
            // Technische Dezimalwerte: 1234.5
            if (/^-?\d+\.\d+$/.test(cleaned)) {
        
                return Number(cleaned);
        
            }
        
            return null;
        }


        function compareValues(valueA, valueB) {

            const emptyA = valueA === "" || valueA === "-";
            const emptyB = valueB === "" || valueB === "-";
        
            // Leere Werte immer ans Ende
            if (emptyA && !emptyB) {
                return 1;
            }
        
            if (!emptyA && emptyB) {
                return -1;
            }
        
            if (emptyA && emptyB) {
                return 0;
            }
        
        
            const dateA = normalizeDate(valueA);
            const dateB = normalizeDate(valueB);
        
            if (dateA !== null && dateB !== null) {
                return dateA - dateB;
            }
        
        
            const numberA = normalizeNumber(valueA);
            const numberB = normalizeNumber(valueB);
        
            if (numberA !== null && numberB !== null) {
                return numberA - numberB;
            }
        
        
            /*
             * Natürliche Textsortierung:
             *
             * ATH001
             * ATH002
             * ATH010
             * BBR001
             * COR063
             */
            return valueA.localeCompare(
                valueB,
                "de",
                {
                    numeric: true,
                    sensitivity: "base",
                    ignorePunctuation: false
                }
            );
        }


        // =====================================
        // FILTER
        // =====================================

        function filterRows() {

            const searchTerm = searchInput
                ? searchInput.value.trim().toLowerCase()
                : "";

            if (!searchTerm) {
                filteredRows = [...allRows];
                return;
            }

            filteredRows = allRows.filter(row => {

                const text = row.innerText
                    .replace(/\s+/g, " ")
                    .trim()
                    .toLowerCase();

                return text.includes(searchTerm);

            });

        }


        // =====================================
        // SORT
        // Wichtig:
        // Es werden ALLE Zeilen sortiert, nicht nur Seite 1.
        // =====================================

        function sortRows() {

            if (sortColumnIndex === null) {
                return;
            }

            allRows.sort((rowA, rowB) => {

                const valueA = getCellText(
                    rowA,
                    sortColumnIndex
                );

                const valueB = getCellText(
                    rowB,
                    sortColumnIndex
                );

                const result = compareValues(
                    valueA,
                    valueB
                );

                return sortDirection === "asc"
                    ? result
                    : result * -1;

            });

        }


        // =====================================
        // RENDER
        // =====================================

        function renderRows() {

            const startIndex = (currentPage - 1) * perPage;
            const endIndex = startIndex + perPage;

            const visibleRows = new Set(
                filteredRows.slice(
                    startIndex,
                    endIndex
                )
            );

            // Alle Zeilen bleiben im DOM.
            // Dadurch funktionieren Spaltenauswahl, Suche und Sortierung stabil.
            allRows.forEach(row => {

                tbody.appendChild(row);

                row.style.display = visibleRows.has(row)
                    ? ""
                    : "none";

            });

        }


        // =====================================
        // PAGINATION
        // =====================================

        function renderPagination() {

            if (!pagination) {
                return;
            }

            pagination.innerHTML = "";

            const pageCount = Math.ceil(
                filteredRows.length / perPage
            );

            if (pageCount <= 1) {
                return;
            }


            const prevButton = document.createElement("button");

            prevButton.type = "button";
            prevButton.className = "fos-page-btn";
            prevButton.innerText = "‹";
            prevButton.disabled = currentPage === 1;

            prevButton.addEventListener("click", () => {

                if (currentPage > 1) {
                    currentPage--;
                    applyTable();
                }

            });

            pagination.appendChild(prevButton);


            for (let page = 1; page <= pageCount; page++) {

                const button = document.createElement("button");

                button.type = "button";
                button.className = "fos-page-btn";
                button.innerText = page;

                if (page === currentPage) {
                    button.classList.add("active");
                }

                button.addEventListener("click", () => {

                    currentPage = page;
                    applyTable();

                });

                pagination.appendChild(button);

            }


            const nextButton = document.createElement("button");

            nextButton.type = "button";
            nextButton.className = "fos-page-btn";
            nextButton.innerText = "›";
            nextButton.disabled = currentPage === pageCount;

            nextButton.addEventListener("click", () => {

                if (currentPage < pageCount) {
                    currentPage++;
                    applyTable();
                }

            });

            pagination.appendChild(nextButton);

        }


        // =====================================
        // SORT INDICATORS
        // =====================================

        function updateSortIndicators() {

            const headers = table.querySelectorAll("thead th");

            headers.forEach((header, index) => {

                header.classList.remove(
                    "sorted-asc",
                    "sorted-desc"
                );

                let indicator = header.querySelector(".sort-indicator");

                if (!indicator) {

                    indicator = document.createElement("span");
                    indicator.className = "sort-indicator";
                    indicator.innerText = "↕";

                    header.appendChild(
                        document.createTextNode(" ")
                    );

                    header.appendChild(indicator);

                }

                indicator.innerText = "↕";

                if (index === sortColumnIndex) {

                    if (sortDirection === "asc") {
                        header.classList.add("sorted-asc");
                        indicator.innerText = "↑";
                    } else {
                        header.classList.add("sorted-desc");
                        indicator.innerText = "↓";
                    }

                }

            });

        }


        // =====================================
        // APPLY TABLE
        // Reihenfolge:
        // 1. Sortieren
        // 2. Filtern
        // 3. Seite berechnen
        // 4. Rendern
        // =====================================

        function applyTable() {

            sortRows();
            filterRows();

            const pageCount = Math.max(
                1,
                Math.ceil(filteredRows.length / perPage)
            );

            if (currentPage > pageCount) {
                currentPage = pageCount;
            }

            renderRows();
            renderPagination();
            updateSortIndicators();

        }


        // =====================================
        // EVENTS: SEARCH
        // =====================================

        if (searchInput) {

            searchInput.addEventListener("input", () => {

                currentPage = 1;
                applyTable();

            });

        }


        // =====================================
        // EVENTS: SORTING
        // =====================================

        const headers = table.querySelectorAll("thead th");

        headers.forEach((header, index) => {

            header.style.cursor = "pointer";

            header.addEventListener("click", () => {

                if (sortColumnIndex === index) {

                    sortDirection = sortDirection === "asc"
                        ? "desc"
                        : "asc";

                } else {

                    sortColumnIndex = index;
                    sortDirection = "asc";

                }

                currentPage = 1;
                applyTable();

            });

        });


        // =====================================
        // INIT
        // =====================================

        applyTable();

    });

});
