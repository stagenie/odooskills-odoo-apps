/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ProductSearch } from "./product_search";
import { ScanBanner } from "./scan_banner";
import { ScanFeedback } from "./scan_feedback";

export class BarcodeConsult extends Component {
    static template = "oski_stock_barcode.BarcodeConsult";
    static components = { ProductSearch, ScanBanner };
    static props = { onBack: Function };

    setup() {
        this.notification = useService("notification");
        const barcodeService = useService("barcode");
        useBus(barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScan(ev));

        this.state = useState({
            mode: 'scan',
            // Résultat affiché : produit ou emplacement
            viewType: false, // 'product' | 'location' | false
            product: false,
            location: false,
            recentMoves: [],
            loading: false,
            lastScan: '',
            lastScanStatus: '',
        });
    }

    async _onBarcodeScan(ev) {
        const barcode = ev.detail.barcode;
        // D'abord essayer comme produit
        const result = await rpc('/oski_stock_barcode/scan_product', { barcode });
        if (result.found) {
            this.state.lastScan = result.name;
            this.state.lastScanStatus = 'success';
            ScanFeedback.success();
            await this._loadProductInfo(result.id);
            return;
        }
        // Sinon essayer comme emplacement
        const locResult = await rpc('/oski_stock_barcode/scan_location', { barcode });
        if (locResult.found) {
            this.state.lastScan = locResult.name;
            this.state.lastScanStatus = 'success';
            ScanFeedback.success();
            await this._loadLocationInfo(locResult.id);
            return;
        }
        this.state.lastScan = barcode;
        this.state.lastScanStatus = 'error';
        ScanFeedback.error();
        this.notification.add(`Article/emplacement inconnu: ${barcode}`, { type: 'danger' });
    }

    async _onProductSelected(product) {
        await this._loadProductInfo(product.id);
    }

    async _loadProductInfo(productId) {
        this.state.loading = true;
        try {
            const info = await rpc('/oski_stock_barcode/get_product_info', {
                product_id: productId,
            });
            if (info.error) {
                this.notification.add(info.error, { type: 'danger' });
                this._clear();
            } else {
                this.state.product = info;
                this.state.location = false;
                this.state.viewType = 'product';
                this.state.recentMoves = [];
            }
        } catch {
            this.notification.add("Erreur de chargement", { type: 'danger' });
            this._clear();
        }
        if (this.state.viewType === 'product' && this.state.product) {
            try {
                const mv = await rpc('/oski_stock_barcode/get_product_moves',
                    { product_id: productId });
                this.state.recentMoves = mv.moves || [];
            } catch {
                this.state.recentMoves = [];
            }
        }
        this.state.loading = false;
    }

    async _loadLocationInfo(locationId) {
        this.state.loading = true;
        try {
            const info = await rpc('/oski_stock_barcode/get_location_info', {
                location_id: locationId,
            });
            if (info.error) {
                this.notification.add(info.error, { type: 'danger' });
                this._clear();
            } else {
                this.state.location = info;
                this.state.product = false;
                this.state.recentMoves = [];
                this.state.viewType = 'location';
            }
        } catch {
            this.notification.add("Erreur de chargement", { type: 'danger' });
            this._clear();
        }
        this.state.loading = false;
    }

    _setMode(mode) { this.state.mode = mode; }

    _clear() {
        this.state.product = false;
        this.state.location = false;
        this.state.recentMoves = [];
        this.state.viewType = false;
    }

    _stockClass(available) {
        if (available <= 0) return 'text-danger fw-bold';
        if (available < 5) return 'text-warning fw-bold';
        return 'text-success fw-bold';
    }
}
