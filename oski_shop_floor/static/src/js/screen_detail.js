/** @odoo-module **/

import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useShopFloorScan } from "./use_shop_floor_scan";
import { scanFeedback } from "./scan_feedback";
import { _t } from "@web/core/l10n/translation";

export class ScreenDetail extends Component {
    static template = "oski_shop_floor.ScreenDetail";
    static props = { detail: Object, orderId: [Number, Boolean], onBack: Function };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ detail: this._stamp(this.props.detail), now: Date.now() });
        // Le chronomètre avance d'une seconde à la fois, sans appel serveur.
        const ticker = setInterval(() => { this.state.now = Date.now(); }, 1000);
        onWillUnmount(() => clearInterval(ticker));
        useShopFloorScan((code) => this.onScan(code));
    }

    /** Heure de réception des données : point de départ des secondes qui défilent. */
    _stamp(detail) {
        return detail ? { ...detail, loaded_at: Date.now() } : detail;
    }

    _clock(minutes) {
        const total = Math.max(0, Math.floor(minutes * 60));
        const pad = (n) => String(n).padStart(2, "0");
        return `${pad(Math.floor(total / 3600))}:${pad(Math.floor((total % 3600) / 60))}:${pad(total % 60)}`;
    }

    get timer() {
        const wo = this.wo;
        const live = wo.running ? (this.state.now - wo.loaded_at) / 60000 : 0;
        return this._clock((wo.elapsed || 0) + live);
    }

    get expected() {
        return _t("%s expected", this._clock(this.wo.duration_expected || 0));
    }

    get wo() {
        return this.state.detail;
    }

    get stateLabel() {
        const labels = {
            ready: _t("To Do"),
            progress: _t("In Progress"),
            done: _t("Finished"),
            cancel: _t("Cancelled"),
            pending: _t("Waiting"),
            waiting: _t("Waiting"),
        };
        return labels[this.wo.state] || this.wo.state;
    }

    async _call(method, args = []) {
        try {
            this.state.detail = this._stamp(await this.orm.call(
                "mrp.workorder", method, [[this.props.orderId], ...args]
            ));
            this._warnConsumption(this.state.detail);
        } catch (e) {
            this.notification.add(e.data?.message || e.message || _t("Error"), { type: "danger" });
        }
    }

    _warnConsumption(detail) {
        if (detail?.over_demand) {
            this.notification.add(_t("Consumed quantity is higher than the planned quantity."), { type: "warning" });
        }
        if (detail?.needs_lot) {
            this.notification.add(
                _t("Component tracked by lot or serial number: enter it in the manufacturing order."),
                { type: "warning" }
            );
        }
    }

    start() { return this._call("sf_start"); }
    pause() { return this._call("sf_pause"); }

    async finish() {
        // sf_finish() clôt l'OT (state='done') : il ne reste plus sur ce
        // poste, donc l'écran Détail n'a plus de raison d'être affiché.
        // On ne retourne à la liste des ordres qu'en cas de succès — une
        // sf_finish() qui lève UserError (OT pas en cours) ne doit pas
        // faire naviguer l'opérateur ailleurs.
        try {
            this.state.detail = this._stamp(await this.orm.call(
                "mrp.workorder", "sf_finish", [[this.props.orderId]]
            ));
            this.props.onBack();
        } catch (e) {
            this.notification.add(e.data?.message || e.message || _t("Error"), { type: "danger" });
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
                this.state.detail = this._stamp(res.detail);
                scanFeedback(true);
                this._warnConsumption(res.detail);
            } else {
                scanFeedback(false);
                this.notification.add(_t("Unrecognized code: %s", code), { type: "warning" });
            }
        } catch (e) {
            scanFeedback(false);
            this.notification.add(e.data?.message || e.message || _t("Scan error"), { type: "danger" });
        }
    }
}
