/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class BarcodeSession extends Component {
    static template = "oski_stock_barcode.BarcodeSession";
    static props = { onBack: Function };

    setup() {
        this.notification = useService("notification");
        this.state = useState({ lines: [], summary: {}, loading: true });
        onMounted(() => this._load());
    }

    async _load() {
        this.state.loading = true;
        try {
            const res = await rpc('/oski_stock_barcode/get_session_log', {});
            this.state.lines = res.lines || [];
            this.state.summary = res.summary || {};
        } catch {
            this.notification.add("Erreur de chargement", { type: 'danger' });
        }
        this.state.loading = false;
    }

    get summaryList() {
        return Object.keys(this.state.summary).map(k => ({
            key: k, ...this.state.summary[k],
        }));
    }
}
