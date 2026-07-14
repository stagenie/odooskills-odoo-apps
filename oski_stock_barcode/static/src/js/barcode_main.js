/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { PickingList } from "./picking_list";
import { BarcodeReceipt } from "./barcode_receipt";
import { BarcodeDelivery } from "./barcode_delivery";
import { BarcodeInventory } from "./barcode_inventory";
import { BarcodeTransfer } from "./barcode_transfer";
import { BarcodeConsult } from "./barcode_consult";
import { BarcodeSession } from "./barcode_session";

export class BarcodeMain extends Component {
    static template = "oski_stock_barcode.BarcodeMain";
    static components = { PickingList, BarcodeReceipt, BarcodeDelivery, BarcodeInventory, BarcodeTransfer, BarcodeConsult, BarcodeSession };

    setup() {
        this.state = useState({
            currentScreen: 'home',
            counts: { incoming: 0, outgoing: 0, internal: 0 },
            selectedPickingId: false,
            selectedPickingType: '',
        });
        onMounted(() => this._loadCounts());
    }

    async _loadCounts() {
        try {
            this.state.counts = await rpc('/oski_stock_barcode/picking_counts', {});
        } catch { /* silent */ }
    }

    _navigate(screen) { this.state.currentScreen = screen; }

    _goHome() {
        this.state.currentScreen = 'home';
        this.state.selectedPickingId = false;
        this._loadCounts();
    }

    _onPickingSelected(pickingId) {
        this.state.selectedPickingId = pickingId;
        if (this.state.currentScreen === 'receipt_list') {
            this.state.currentScreen = 'receipt_detail';
        } else if (this.state.currentScreen === 'delivery_list') {
            this.state.currentScreen = 'delivery_detail';
        }
    }

    _backToList() {
        if (this.state.currentScreen === 'receipt_detail') {
            this.state.currentScreen = 'receipt_list';
        } else if (this.state.currentScreen === 'delivery_detail') {
            this.state.currentScreen = 'delivery_list';
        }
        this.state.selectedPickingId = false;
        // Rafraîchir les compteurs de la page d'accueil
        this._loadCounts();
    }
}

registry.category("actions").add("oski_barcode_main", BarcodeMain);
