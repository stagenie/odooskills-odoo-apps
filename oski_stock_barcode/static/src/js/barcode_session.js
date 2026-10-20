/** @odoo-module **/

import { Component, onMounted, proxy, usePlugin, useProps, t } from "@odoo/owl";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { barcodeRpc } from "./barcode_rpc";

export class BarcodeSession extends Component {
    static template = "oski_stock_barcode.BarcodeSession";
    props = useProps({ onBack: t.function() });

    setup() {
        this.notification = usePlugin(NotificationPlugin);
        this.state = proxy({ lines: [], summary: {}, loading: true });
        onMounted(() => this._load());
    }

    async _load() {
        this.state.loading = true;
        try {
            const res = await barcodeRpc('/oski_stock_barcode/get_session_log', {});
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
