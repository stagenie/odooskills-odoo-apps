// Demande d'évolution : un seul envoi par clic (bouton désactivé au submit).
(function () {
    "use strict";
    function start() {
        document.querySelectorAll("form.oski-fb-form").forEach((form) => {
            form.addEventListener("submit", () => {
                const button = form.querySelector(".oski-fb-submit");
                if (button) {
                    window.setTimeout(() => { button.disabled = true; }, 0);
                }
            });
        });
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
