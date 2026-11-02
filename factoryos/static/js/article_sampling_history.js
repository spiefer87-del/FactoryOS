document.addEventListener("DOMContentLoaded", function () {
    "use strict";
    document.querySelectorAll("[data-article-history-popup]").forEach(function (link) {
        link.addEventListener("click", function (event) {
            if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            // Without JS, or if the popup is blocked, the ordinary link still works.
            try {
                const popup = window.open(link.href, "_blank", "popup=yes,width=1200,height=850,scrollbars=yes,resizable=yes");
                if (popup) {
                    popup.opener = null;
                    event.preventDefault();
                }
            } catch (_) { /* Keep the normal link navigation. */ }
        });
    });
});
