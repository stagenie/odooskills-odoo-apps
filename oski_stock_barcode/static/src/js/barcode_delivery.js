/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ProductSearch } from "./product_search";
import { QtyStepper } from "./qty_stepper";
import { ScanBanner } from "./scan_banner";
import { ScanFeedback } from "./scan_feedback";

export class BarcodeDelivery extends Component {
    static template = "oski_stock_barcode.BarcodeDelivery";
    static components = { ProductSearch, QtyStepper, ScanBanner };
    static props = { onBack: Function, pickingId: Number };

    setup() {
        this.notification = useService("notification");
        const barcodeService = useService("barcode");
        useBus(barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScan(ev));

        this.state = useState({
            lines: [],
            mode: 'scan',
            pickingName: '',
            partnerName: '',
            origin: '',
            lastScan: '',
            lastScanStatus: '',
            validated: false,
            validationMessage: '',
        });
        onMounted(() => this._loadLines());
    }

    async _loadLines() {
        const data = await rpc('/oski_stock_barcode/get_picking_lines', { picking_id: this.props.pickingId });
        if (data.error) { this.notification.add(data.error, { type: 'danger' }); return; }
        Object.assign(this.state, {
            lines: data.lines, pickingName: data.picking_name,
            partnerName: data.partner_name, origin: data.origin || '',
        });
    }

    async _onBarcodeScan(ev) {
        const barcode = ev.detail.barcode;
        const result = await rpc('/oski_stock_barcode/scan_product', { barcode, picking_id: this.props.pickingId });
        if (!result.found) {
            this.state.lastScan = barcode; this.state.lastScanStatus = 'error';
            ScanFeedback.error();
            this.notification.add(`Article inconnu: ${barcode}`, { type: 'danger' }); return;
        }
        this.state.lastScan = result.name;
        const line = this.state.lines.find(l => l.product_id === result.id);
        if (line) {
            const maxQty = Math.min(line.demand_qty, line.available_qty);
            if (line.done_qty >= maxQty) {
                this.state.lastScanStatus = 'error';
                ScanFeedback.warning();
                this.notification.add(
                    `${result.name} — ${line.available_qty < line.demand_qty ? 'stock insuffisant' : 'quantité max atteinte'}`,
                    { type: 'warning' }
                );
                return;
            }
            line.done_qty += 1;
            await this._updateQty(line.product_id, line.done_qty);
            this.state.lastScanStatus = 'success';
            ScanFeedback.success();
        } else {
            this.state.lastScanStatus = 'error';
            ScanFeedback.warning();
            this.notification.add(`${result.name} — pas dans cette livraison`, { type: 'warning' });
        }
    }

    _onProductSelected(product) {
        const line = this.state.lines.find(l => l.product_id === product.id);
        if (!line) { this.notification.add(`${product.name} — pas dans cette livraison`, { type: 'warning' }); return; }
        const maxQty = Math.min(line.demand_qty, line.available_qty);
        if (line.done_qty >= maxQty) {
            this.notification.add(`${product.name} — ${line.available_qty < line.demand_qty ? 'stock insuffisant' : 'quantité max'}`, { type: 'warning' });
            return;
        }
        line.done_qty += 1;
        this._updateQty(line.product_id, line.done_qty);
    }

    async _onQtyChange(line, qty) {
        const maxQty = Math.min(line.demand_qty, line.available_qty);
        if (qty > maxQty) {
            qty = maxQty;
            this.notification.add(
                `Limité à ${maxQty} (${line.available_qty < line.demand_qty ? 'stock insuffisant' : 'demande atteinte'})`,
                { type: 'warning' }
            );
        }
        line.done_qty = qty;
        await this._updateQty(line.product_id, qty);
    }

    async _updateQty(productId, qty) {
        const r = await rpc('/oski_stock_barcode/update_line_qty', { picking_id: this.props.pickingId, product_id: productId, qty });
        if (r.error) {
            this.notification.add(r.error, { type: 'danger' });
            await this._loadLines();
        }
    }

    _lineMaxQty(line) {
        return Math.min(line.demand_qty || 0, line.available_qty || 0);
    }
    _lineClass(line) {
        if (line.done_qty >= line.demand_qty && line.demand_qty > 0) return 'o_line_complete';
        return '';
    }
    _availClass(line) {
        if (line.available_qty < line.demand_qty) return 'text-danger fw-bold';
        return 'text-muted';
    }
    _setMode(mode) { this.state.mode = mode; }
    get allComplete() { return this.state.lines.length > 0 && this.state.lines.every(l => l.done_qty >= l.demand_qty); }
    get hasAnyQty() { return this.state.lines.some(l => l.done_qty > 0); }
    get totalDemand() { return this.state.lines.reduce((s, l) => s + l.demand_qty, 0); }
    get totalDone() { return this.state.lines.reduce((s, l) => s + l.done_qty, 0); }

    async _validate() {
        const r = await rpc('/oski_stock_barcode/validate_picking', {
            picking_id: this.props.pickingId,
            create_backorder: true,
        });
        if (r.error) {
            this.notification.add(r.error, { type: 'danger' });
            return;
        }
        let msg = "Livraison validée !";
        if (r.is_partial && r.backorder_created) {
            msg += ` Reliquat créé : ${r.backorder_name}`;
        }
        this.state.validated = true;
        this.state.validationMessage = msg;
        this.notification.add(msg, { type: 'success' });
    }
    async _printSlip() {
        const res = await rpc('/oski_stock_barcode/get_report_url',
            { picking_id: this.props.pickingId });
        if (res.error) { this.notification.add(res.error, { type: 'danger' }); return; }
        window.open(res.url, '_blank');
    }
    async _refresh() { await this._loadLines(); }
}
