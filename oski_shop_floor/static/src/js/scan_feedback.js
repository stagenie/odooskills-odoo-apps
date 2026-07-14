/** @odoo-module **/

// Retour sensoriel local, indépendant du module oski_stock_barcode.
export function scanFeedback(ok = true) {
    try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (Ctx) {
            const ctx = new Ctx();
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
