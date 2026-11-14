// Essai 1 h : page d'attente. Sonde l'état via le store (jamais le service
// d'essai directement) toutes les 3 s, puis ouvre la base quand elle est prête.
// Démarre même si DOMContentLoaded est déjà passé (bundle chargé en différé).
(function () {
    "use strict";
    const POLL_MS = 3000;

    function start() {
        const box = document.querySelector(".oski-trial-wait");
        if (!box || box.dataset.oskiTrialStarted) {
            return;
        }
        box.dataset.oskiTrialStarted = "1";
        const openUrl = box.dataset.openUrl;
        if (box.dataset.autoOpen && openUrl) {
            window.location.assign(openUrl);
            return;
        }
        const statusUrl = box.dataset.statusUrl;
        if (!statusUrl) {
            return;
        }
        const message = box.querySelector(".oski-trial-message");

        async function poll() {
            let data = null;
            try {
                const res = await fetch(statusUrl, {
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: { Accept: "application/json" },
                });
                if (res.ok) {
                    data = await res.json();
                }
            } catch {
                data = null; // réseau coupé : on réessaie au tour suivant
            }
            if (data) {
                if (message && data.message) {
                    message.textContent = data.message;
                }
                box.dataset.state = data.state;
                if (data.state === "ready" && data.open_url) {
                    window.location.assign(data.open_url);
                    return;
                }
                if (!data.pending) {
                    // État final (terminé, échec, refus) : la page serveur
                    // affiche les bons boutons.
                    window.location.reload();
                    return;
                }
            }
            window.setTimeout(poll, POLL_MS);
        }
        window.setTimeout(poll, POLL_MS);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
