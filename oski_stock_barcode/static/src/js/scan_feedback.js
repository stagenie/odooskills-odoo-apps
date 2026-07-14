/** @odoo-module **/

/**
 * Feedback sensoriel pour les scans barcode.
 * Son via Web Audio API (pas de fichier audio nécessaire) + vibration mobile.
 */

let _audioCtx = null;

function _getAudioCtx() {
    if (!_audioCtx) {
        try {
            _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        } catch {
            // Web Audio non supporté
        }
    }
    return _audioCtx;
}

function _playTone(frequency, duration, type = 'sine') {
    const ctx = _getAudioCtx();
    if (!ctx) return;
    // Résumer le contexte si suspendu (politique autoplay navigateur)
    if (ctx.state === 'suspended') {
        ctx.resume();
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = type;
    osc.frequency.value = frequency;
    gain.gain.value = 0.3;
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration);
}

function _vibrate(pattern) {
    if (navigator.vibrate) {
        navigator.vibrate(pattern);
    }
}

export const ScanFeedback = {
    /** Bip court aigu — scan réussi */
    success() {
        _playTone(880, 0.15, 'sine');
        _vibrate(100);
    },

    /** Double buzz grave — scan échoué */
    error() {
        _playTone(220, 0.1, 'square');
        setTimeout(() => _playTone(180, 0.15, 'square'), 120);
        _vibrate([100, 50, 100]);
    },

    /** Bip moyen — attention/warning */
    warning() {
        _playTone(440, 0.2, 'triangle');
        _vibrate([50, 30, 50]);
    },
};
