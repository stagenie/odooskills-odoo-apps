/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ProductSearch } from "./product_search";
import { QtyStepper } from "./qty_stepper";
import { ScanBanner } from "./scan_banner";
import { ScanFeedback } from "./scan_feedback";

export class BarcodeTransfer extends Component {
    static template = "oski_stock_barcode.BarcodeTransfer";
    static components = { ProductSearch, QtyStepper, ScanBanner };
    static props = { onBack: Function };

    setup() {
        this.notification = useService("notification");
        const barcodeService = useService("barcode");
        useBus(barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScan(ev));

        this.state = useState({
            // Phase 'prepare' = saisie articles, 'detail' = ajuster qté + valider
            screen: 'prepare',
            locations: [],
            srcLocationId: false,
            destLocationId: false,
            items: [],
            mode: 'scan',
            lastScan: '',
            lastScanStatus: '',
            // Phase detail (après création picking)
            pickingId: false,
            pickingName: '',
            lines: [],
            // Phase validated
            validated: false,
            validationMessage: '',
        });
        onMounted(() => this._loadLocations());
    }

    async _loadLocations() {
        this.state.locations = await rpc('/oski_stock_barcode/get_locations', {});
    }

    _onSrcChange(ev) { this.state.srcLocationId = parseInt(ev.target.value, 10) || false; this.state.items = []; }
    _onDestChange(ev) { this.state.destLocationId = parseInt(ev.target.value, 10) || false; }

    async _onBarcodeScan(ev) {
        if (this.state.screen !== 'prepare') return;
        if (!this.state.srcLocationId || !this.state.destLocationId) {
            this.notification.add("Sélectionnez les emplacements", { type: 'warning' }); return;
        }
        const barcode = ev.detail.barcode;
        const result = await rpc('/oski_stock_barcode/scan_product', { barcode });
        if (!result.found) {
            this.state.lastScan = barcode; this.state.lastScanStatus = 'error';
            ScanFeedback.error();
            this.notification.add(`Article inconnu: ${barcode}`, { type: 'danger' }); return;
        }
        this.state.lastScan = result.name;
        this.state.lastScanStatus = 'success';
        ScanFeedback.success();
        await this._addOrIncrementProduct(result);
    }

    async _onProductSelected(product) {
        if (!this.state.srcLocationId || !this.state.destLocationId) {
            this.notification.add("Sélectionnez les emplacements", { type: 'warning' }); return;
        }
        await this._addOrIncrementProduct(product);
    }

    async _addOrIncrementProduct(product) {
        const existing = this.state.items.find(i => i.product_id === product.id);
        if (existing) { existing.qty += 1; return; }
        const quantInfo = await rpc('/oski_stock_barcode/get_quant_info', {
            product_id: product.id, location_id: this.state.srcLocationId,
        });
        this.state.items.push({
            product_id: product.id,
            product_name: product.name,
            qty: 1,
            available_qty: quantInfo.available_quantity,
        });
    }

    _onQtyChange(item, qty) {
        if (qty > item.available_qty) {
            this.notification.add(`Stock insuffisant (${item.available_qty} dispo)`, { type: 'warning' });
            qty = item.available_qty;
        }
        item.qty = qty;
    }

    _setMode(mode) { this.state.mode = mode; }
    _removeItem(index) { this.state.items.splice(index, 1); }

    get canConfirm() {
        return this.state.srcLocationId && this.state.destLocationId &&
            this.state.srcLocationId !== this.state.destLocationId && this.state.items.length > 0;
    }

    // ── Phase 1 : créer le picking (sans valider) ──
    async _confirmTransfer() {
        if (!this.canConfirm) return;
        const items = this.state.items.map(i => ({ product_id: i.product_id, qty: i.qty }));
        const result = await rpc('/oski_stock_barcode/create_transfer', {
            src_location_id: this.state.srcLocationId,
            dest_location_id: this.state.destLocationId, items,
        });
        if (result.error) {
            this.notification.add(result.error, { type: 'danger' });
            return;
        }
        // Passer en mode détail pour ajuster et valider
        this.state.pickingId = result.picking_id;
        this.state.pickingName = result.picking_name;
        this.state.screen = 'detail';
        await this._loadLines();
    }

    // ── Phase 2 : charger les lignes du picking créé ──
    async _loadLines() {
        const data = await rpc('/oski_stock_barcode/get_picking_lines', {
            picking_id: this.state.pickingId,
        });
        if (data.error) {
            this.notification.add(data.error, { type: 'danger' });
            return;
        }
        this.state.lines = data.lines;
    }

    async _onLineQtyChange(line, qty) {
        const maxQty = Math.min(line.demand_qty, line.available_qty);
        if (qty > maxQty) {
            qty = maxQty;
            this.notification.add(
                `Limité à ${maxQty} (${line.available_qty < line.demand_qty ? 'stock insuffisant' : 'demande atteinte'})`,
                { type: 'warning' }
            );
        }
        line.done_qty = qty;
        await rpc('/oski_stock_barcode/update_line_qty', {
            picking_id: this.state.pickingId,
            product_id: line.product_id, qty,
        });
    }

    _lineClass(line) {
        if (line.done_qty >= line.demand_qty && line.demand_qty > 0) return 'o_line_complete';
        return '';
    }

    get allComplete() {
        return this.state.lines.length > 0 && this.state.lines.every(l => l.done_qty >= l.demand_qty);
    }
    get hasAnyQty() { return this.state.lines.some(l => l.done_qty > 0); }
    get totalDemand() { return this.state.lines.reduce((s, l) => s + l.demand_qty, 0); }
    get totalDone() { return this.state.lines.reduce((s, l) => s + l.done_qty, 0); }

    // ── Phase 3 : valider (avec backorder si partiel) ──
    async _validateTransfer() {
        const r = await rpc('/oski_stock_barcode/validate_picking', {
            picking_id: this.state.pickingId,
            create_backorder: true,
        });
        if (r.error) {
            this.notification.add(r.error, { type: 'danger' });
            return;
        }
        let msg = `Transfert ${this.state.pickingName} validé !`;
        if (r.is_partial && r.backorder_created) {
            msg += ` Reliquat créé : ${r.backorder_name}`;
        }
        this.state.validated = true;
        this.state.validationMessage = msg;
        this.notification.add(msg, { type: 'success' });
    }

    // ── Impression ──
    async _printPicking() {
        const r = await rpc('/oski_stock_barcode/get_report_url', {
            picking_id: this.state.pickingId,
        });
        if (r.error) {
            this.notification.add(r.error, { type: 'danger' });
            return;
        }
        window.open(r.url, '_blank');
    }

    _backToPrepare() {
        this.state.screen = 'prepare';
        this.state.pickingId = false;
        this.state.pickingName = '';
        this.state.lines = [];
        this.state.items = [];
        this.state.validated = false;
        this.state.validationMessage = '';
    }

    async _refresh() { await this._loadLines(); }
}
