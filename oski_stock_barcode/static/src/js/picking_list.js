/** @odoo-module **/

import { Component, onMounted, proxy, usePlugin, signal, useProps, t } from "@odoo/owl";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { useBus } from "@web/core/utils/hooks";
import { barcodeRpc } from "./barcode_rpc";
import { BarcodePlugin } from "@barcodes/barcode_plugin";
import { ScanFeedback } from "./scan_feedback";

export class PickingList extends Component {
    static template = "oski_stock_barcode.PickingList";
    props = useProps({
        pickingTypeCode: t.string(),
        title: t.string(),
        onPickingSelected: t.function(),
        onBack: t.function(),
    });

    setup() {
        this.notification = usePlugin(NotificationPlugin);
        const barcodeService = usePlugin(BarcodePlugin);
        useBus(barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScan(ev));

        this.state = proxy({
            pickings: [],
            filter: '',
            loading: true,
        });
        this.filterRef = signal.ref();

        onMounted(() => this._loadPickings());
    }

    async _loadPickings() {
        this.state.loading = true;
        try {
            this.state.pickings = await barcodeRpc('/oski_stock_barcode/get_pickings', {
                picking_type_code: this.props.pickingTypeCode,
            });
        } catch {
            this.notification.add("Erreur de chargement", { type: 'danger' });
        }
        this.state.loading = false;
    }

    get filteredPickings() {
        const q = this.state.filter.toLowerCase();
        if (!q) return this.state.pickings;
        return this.state.pickings.filter(p =>
            (p.name || '').toLowerCase().includes(q) ||
            (p.partner_name || '').toLowerCase().includes(q) ||
            (p.origin || '').toLowerCase().includes(q)
        );
    }

    _onFilterInput(ev) {
        this.state.filter = ev.target.value;
    }

    async _onBarcodeScan(ev) {
        const barcode = ev.detail.barcode;
        const result = await barcodeRpc('/oski_stock_barcode/scan_picking', {
            barcode: barcode,
            picking_type_code: this.props.pickingTypeCode,
        });
        if (result.found) {
            ScanFeedback.success();
            this.notification.add(`${result.picking.name} trouvé`, { type: 'success' });
            this.props.onPickingSelected(result.picking.id);
        } else {
            ScanFeedback.error();
            this.notification.add(`Aucun bon trouvé: ${barcode}`, { type: 'warning' });
        }
    }

    _selectPicking(pickingId) {
        this.props.onPickingSelected(pickingId);
    }

    _stateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'waiting': 'En attente',
            'confirmed': 'En attente',
            'assigned': 'Prêt',
        };
        return labels[state] || state;
    }

    _stateBadgeClass(state) {
        if (state === 'assigned') return 'text-bg-success';
        if (state === 'confirmed' || state === 'waiting') return 'text-bg-warning';
        return 'text-bg-secondary';
    }

    _progressPercent(p) {
        if (!p.total_lines) return 0;
        return Math.round((p.done_lines / p.total_lines) * 100);
    }
}
