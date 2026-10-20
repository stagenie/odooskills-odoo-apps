/** @odoo-module **/

import { Component, proxy, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useShopFloorScan } from "./use_shop_floor_scan";
import { scanFeedback } from "./scan_feedback";

export class ScreenDetail extends Component {
    static template = "oski_shop_floor.ScreenDetail";
    props = useProps({
        detail: t.object(),
        orderId: t.or([t.number(), t.boolean()]),
        onBack: t.function(),
    });

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = proxy({ detail: this.props.detail });
        useShopFloorScan((code) => this.onScan(code));
    }

    get wo() {
        return this.state.detail;
    }

    get stateLabel() {
        const labels = {
            ready: "À faire",
            progress: "En cours",
            done: "Terminé",
            cancel: "Annulé",
            blocked: "Bloqué",
        };
        return labels[this.wo.state] || this.wo.state;
    }

    async _call(method, args = []) {
        try {
            this.state.detail = await this.orm.call(
                "mrp.workorder", method, [[this.props.orderId], ...args]
            );
            this._warnConsumption(this.state.detail);
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        }
    }

    _warnConsumption(detail) {
        if (detail?.over_demand) {
            this.notification.add("Quantité consommée supérieure à la quantité prévue.", { type: "warning" });
        }
        if (detail?.needs_lot) {
            this.notification.add(
                "Composant suivi par lot ou numéro de série : renseignez-le dans l'ordre de fabrication.",
                { type: "warning" }
            );
        }
    }

    // Double clic sur Démarrer / Pause / Terminer : une seule requête à la
    // fois (le serveur refuse de toute façon une seconde clôture).
    async _once(fn) {
        if (this._busy) {
            return;
        }
        this._busy = true;
        try {
            return await fn();
        } finally {
            this._busy = false;
        }
    }

    start() { return this._once(() => this._call("sf_start")); }
    pause() { return this._once(() => this._call("sf_pause")); }
    finish() { return this._once(() => this._finish()); }

    async _finish() {
        // sf_finish() clôt l'OT (state='done') : il ne reste plus sur ce
        // poste, donc l'écran Détail n'a plus de raison d'être affiché.
        // On ne retourne à la liste des ordres qu'en cas de succès — une
        // sf_finish() qui lève UserError (OT pas en cours) ne doit pas
        // faire naviguer l'opérateur ailleurs.
        try {
            this.state.detail = await this.orm.call(
                "mrp.workorder", "sf_finish", [[this.props.orderId]]
            );
            this.props.onBack();
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
        }
    }
    setQty(ev) { return this._call("sf_set_qty", [parseFloat(ev.target.value) || 0]); }
    consume(moveId, qty) { return this._call("sf_consume", [moveId, qty]); }

    incComponent(comp) {
        return this.consume(comp.move_id, (comp.qty_done || 0) + 1);
    }

    async onScan(code) {
        try {
            const res = await this.orm.call(
                "mrp.workorder", "sf_scan", [[this.props.orderId], code]
            );
            if (res.found) {
                this.state.detail = res.detail;
                scanFeedback(true);
                this._warnConsumption(res.detail);
            } else {
                scanFeedback(false);
                this.notification.add(`Code non reconnu : ${code}`, { type: "warning" });
            }
        } catch (e) {
            scanFeedback(false);
            this.notification.add(e.data?.message || e.message || "Erreur scan", { type: "danger" });
        }
    }
}
