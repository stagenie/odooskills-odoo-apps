/** @odoo-module **/

// Retour sensoriel local, indépendant du module oski_stock_barcode.
// Un seul AudioContext partagé et réutilisé : les tablettes (WebKit/Safari)
// plafonnent le nombre d'AudioContext "live" simultanés ; en créer un par
// scan finissait par lever une exception (silencieuse) et coupait le bip
// pour le reste de la session.
let _audioCtx = null;

function _getAudioCtx() {
    if (_audioCtx) {
        return _audioCtx;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) {
        return null;
    }
    _audioCtx = new Ctx();
    return _audioCtx;
}

export function scanFeedback(ok = true) {
    try {
        const ctx = _getAudioCtx();
        if (ctx) {
            if (ctx.state === "suspended") {
                // Politique autoplay : le contexte démarre suspendu tant
                // qu'aucun geste utilisateur n'a eu lieu. Reprise best-effort.
                try {
                    ctx.resume();
                } catch (_e) { /* silencieux */ }
            }
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.frequency.value = ok ? 880 : 220;
            gain.gain.value = 0.05;
            osc.connect(gain).connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + (ok ? 0.08 : 0.2));
        }
    } catch (_e) { /* silencieux */ }
    if (navigator.vibrate) {
        navigator.vibrate(ok ? 40 : [60, 40, 60]);
    }
}
