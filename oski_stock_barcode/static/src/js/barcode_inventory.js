/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ProductSearch } from "./product_search";
import { QtyStepper } from "./qty_stepper";
import { ScanBanner } from "./scan_banner";
import { ScanFeedback } from "./scan_feedback";

export class BarcodeInventory extends Component {
    static template = "oski_stock_barcode.BarcodeInventory";
    static components = { ProductSearch, QtyStepper, ScanBanner };
    static props = { onBack: Function };

    setup() {
        this.notification = useService("notification");
        const barcodeService = useService("barcode");
        useBus(barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScan(ev));

        this.state = useState({
            // Navigation : 'locations' ou 'detail'
            screen: 'locations',
            locations: [],
            locationFilter: '',
            selectedLocationId: false,
            selectedLocationName: '',
            items: [],
            mode: 'scan',
            itemFilter: '',
            lastScan: '',
            lastScanStatus: '',
            loading: false,
        });
        onMounted(() => this._loadLocations());
    }

    // ── LOCATIONS LIST ──
    async _loadLocations() {
        this.state.loading = true;
        try {
            this.state.locations = await rpc('/oski_stock_barcode/get_locations', {});
        } catch {
            this.notification.add("Erreur de chargement des emplacements", { type: 'danger' });
            this.state.locations = [];
        }
        this.state.loading = false;
    }

    get filteredLocations() {
        const q = this.state.locationFilter.toLowerCase();
        if (!q) return this.state.locations;
        return this.state.locations.filter(l =>
            (l.complete_name || '').toLowerCase().includes(q) ||
            (l.barcode || '').toLowerCase().includes(q)
        );
    }

    _onLocationFilterInput(ev) {
        this.state.locationFilter = ev.target.value;
    }

    async _selectLocation(loc) {
        this.state.selectedLocationId = loc.id;
        this.state.selectedLocationName = loc.complete_name;
        this.state.screen = 'detail';
        this.state.itemFilter = '';
        await this._loadQuants();
    }

    _backToLocations() {
        this.state.screen = 'locations';
        this.state.selectedLocationId = false;
        this.state.items = [];
        this.state.itemFilter = '';
        this.state.lastScan = '';
    }

    // ── LOCATION BARCODE SCAN ──
    async _onBarcodeScanLocation(barcode) {
        const loc = this.state.locations.find(l =>
            l.barcode === barcode || l.complete_name === barcode || l.name === barcode
        );
        if (loc) {
            ScanFeedback.success();
            this.notification.add(`Emplacement ${loc.complete_name} trouvé`, { type: 'success' });
            await this._selectLocation(loc);
            return true;
        }
        return false;
    }

    // ── QUANTS ──
    async _loadQuants() {
        if (!this.state.selectedLocationId) return;
        this.state.loading = true;
        try {
            const items = await rpc('/oski_stock_barcode/get_location_quants', {
                location_id: this.state.selectedLocationId,
            });
            // Initialiser counted_qty à la quantité système pour chaque ligne
            for (const item of items) {
                item.counted_qty = item.quantity;
                item.touched = false;
            }
            this.state.items = items;
        } catch (e) {
            this.notification.add("Erreur de chargement des articles", { type: 'danger' });
            this.state.items = [];
        }
        this.state.loading = false;
    }

    get filteredItems() {
        const q = this.state.itemFilter.toLowerCase();
        if (!q) return this.state.items;
        return this.state.items.filter(i =>
            (i.product_name || '').toLowerCase().includes(q) ||
            (i.default_code || '').toLowerCase().includes(q) ||
            (i.product_barcode || '').toLowerCase().includes(q)
        );
    }

    _onItemFilterInput(ev) {
        this.state.itemFilter = ev.target.value;
    }

    // ── SCAN / SEARCH ──
    async _onBarcodeScan(ev) {
        const barcode = ev.detail.barcode;

        // Si on est sur la liste des emplacements, chercher un emplacement
        if (this.state.screen === 'locations') {
            const found = await this._onBarcodeScanLocation(barcode);
            if (found) return;
            this.notification.add(`Emplacement inconnu: ${barcode}`, { type: 'warning' });
            return;
        }

        // Sur le détail inventaire, chercher un produit
        if (!this.state.selectedLocationId) return;

        const result = await rpc('/oski_stock_barcode/scan_product', { barcode });
        if (!result.found) {
            this.state.lastScan = barcode;
            this.state.lastScanStatus = 'error';
            ScanFeedback.error();
            this.notification.add(`Article inconnu: ${barcode}`, { type: 'danger' });
            return;
        }
        if (!result.is_storable) {
            this.state.lastScan = result.name;
            this.state.lastScanStatus = 'error';
            ScanFeedback.warning();
            this.notification.add(`${result.name} — article non stockable`, { type: 'warning' });
            return;
        }
        this.state.lastScan = result.name;
        this.state.lastScanStatus = 'success';
        ScanFeedback.success();
        this._incrementProduct(result);
    }

    _onProductSelected(product) {
        if (!this.state.selectedLocationId) return;
        if (product.is_storable === false) {
            this.notification.add(`${product.name} — non stockable`, { type: 'warning' });
            return;
        }
        this._incrementProduct(product);
    }

    _incrementProduct(product) {
        const existing = this.state.items.find(i => i.product_id === product.id);
        if (existing) {
            existing.counted_qty += 1;
            existing.touched = true;
        } else {
            // Nouvel article pas encore en stock à cet emplacement
            this.state.items.push({
                product_id: product.id,
                product_name: product.name,
                product_barcode: product.barcode || '',
                default_code: product.default_code || '',
                quantity: 0,
                reserved_quantity: 0,
                available_quantity: 0,
                counted_qty: 1,
                touched: true,
            });
        }
    }

    _onQtyChange(item, qty) {
        item.counted_qty = qty;
        item.touched = true;
    }

    _ecartClass(item) {
        if (!item.touched) return 'text-muted';
        const diff = item.counted_qty - item.quantity;
        if (diff === 0) return 'text-success';
        return 'text-warning fw-bold';
    }

    _ecartValue(item) {
        if (!item.touched) return '-';
        const diff = item.counted_qty - item.quantity;
        if (diff > 0) return `+${diff}`;
        return `${diff}`;
    }

    _lineClass(item) {
        if (!item.touched) return '';
        const diff = item.counted_qty - item.quantity;
        if (diff === 0) return 'o_line_complete';
        return '';
    }

    _setMode(mode) { this.state.mode = mode; }

    get touchedItems() {
        return this.state.items.filter(i => i.touched);
    }

    get touchedCount() {
        return this.touchedItems.length;
    }

    async _applyLine(item) {
        if (!item.touched) {
            this.notification.add("Aucune modification sur cette ligne", { type: 'warning' });
            return;
        }
        const result = await rpc('/oski_stock_barcode/apply_inventory', {
            location_id: this.state.selectedLocationId,
            items: [{ product_id: item.product_id, counted_qty: item.counted_qty }],
        });
        if (result.error) {
            this.notification.add(result.error, { type: 'danger' });
        } else {
            this.notification.add(`${item.product_name} — inventaire appliqué !`, { type: 'success' });
            item.quantity = item.counted_qty;
            item.touched = false;
        }
    }

    async _applyInventory() {
        const items = this.touchedItems.map(i => ({
            product_id: i.product_id,
            counted_qty: i.counted_qty,
        }));
        if (items.length === 0) {
            this.notification.add("Aucun article modifié", { type: 'warning' });
            return;
        }
        const result = await rpc('/oski_stock_barcode/apply_inventory', {
            location_id: this.state.selectedLocationId, items,
        });
        if (result.error) {
            this.notification.add(result.error, { type: 'danger' });
        } else {
            this.notification.add(`Inventaire appliqué (${items.length} articles) !`, { type: 'success' });
            await this._loadQuants();
        }
    }

    async _refresh() { await this._loadQuants(); }
}
