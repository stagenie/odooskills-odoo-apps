/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useShopFloorScan } from "./use_shop_floor_scan";
import { scanFeedback } from "./scan_feedback";

export class ScreenDetail extends Component {
    static template = "oski_shop_floor.ScreenDetail";
    static props = { detail: Object, orderId: [Number, Boolean], onBack: Function };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ detail: this.props.detail });
        useShopFloorScan((code) => this.onScan(code));
    }

    get wo() {
        return this.state.detail;
    }

    async _call(method, args = []) {
        try {
            this.state.detail = await this.orm.call(
                "mrp.workorder", method, [[this.props.orderId], ...args]
            );
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Erreur", { type: "danger" });
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

    async refresh() {
        this.state.detail = await this.orm.call(
            "mrp.workorder", "sf_get_detail", [[this.props.orderId]]
        );
    }

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
