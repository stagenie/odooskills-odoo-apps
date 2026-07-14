/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ScreenDetail extends Component {
    static template = "oski_shop_floor.ScreenDetail";
    static props = { detail: Object, orderId: [Number, Boolean], onBack: Function };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ detail: this.props.detail });
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
    finish() { return this._call("sf_finish"); }
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
}
