/** @odoo-module **/

import { Component, proxy, onMounted, signal, useProps, t } from "@odoo/owl";
import { barcodeRpc } from "./barcode_rpc";

export class ProductSearch extends Component {
    static template = "oski_stock_barcode.ProductSearch";
    props = useProps({
        onProductSelected: t.function(),
        placeholder: t.string().optional(),
        storableOnly: t.boolean().optional(),
    });

    setup() {
        this.state = proxy({
            query: '',
            results: [],
            loading: false,
            showDropdown: false,
        });
        this.inputRef = signal.ref();
        this._debounceTimer = null;

        onMounted(() => {
            if (this.inputRef()) {
                this.inputRef().focus();
            }
        });
    }

    get placeholder() {
        return this.props.placeholder || "Rechercher par nom, réf ou code-barres...";
    }

    _onInput(ev) {
        this.state.query = ev.target.value;
        clearTimeout(this._debounceTimer);

        if (this.state.query.length < 2) {
            this.state.results = [];
            this.state.showDropdown = false;
            return;
        }

        this.state.loading = true;
        this._debounceTimer = setTimeout(() => this._search(), 300);
    }

    async _search() {
        try {
            const products = await barcodeRpc('/oski_stock_barcode/search_products', {
                query: this.state.query,
                storable_only: this.props.storableOnly || false,
                limit: 10,
            });
            this.state.results = products;
            this.state.showDropdown = products.length > 0;
        } catch {
            this.state.results = [];
            this.state.showDropdown = false;
        }
        this.state.loading = false;
    }

    _onKeydown(ev) {
        if (ev.key === 'Escape') {
            this.state.showDropdown = false;
        }
    }

    _selectProduct(product) {
        this.state.query = '';
        this.state.results = [];
        this.state.showDropdown = false;
        this.props.onProductSelected(product);
        if (this.inputRef()) {
            this.inputRef().focus();
        }
    }

    _onBlur() {
        setTimeout(() => {
            this.state.showDropdown = false;
        }, 200);
    }
}
