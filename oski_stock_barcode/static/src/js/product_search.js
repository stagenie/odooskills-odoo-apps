/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ProductSearch extends Component {
    static template = "oski_stock_barcode.ProductSearch";
    static props = {
        onProductSelected: Function,
        placeholder: { type: String, optional: true },
        storableOnly: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            query: '',
            results: [],
            loading: false,
            showDropdown: false,
        });
        this.inputRef = useRef("searchInput");
        this._debounceTimer = null;

        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
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
            const products = await rpc('/oski_stock_barcode/search_products', {
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
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
    }

    _onBlur() {
        setTimeout(() => {
            this.state.showDropdown = false;
        }, 200);
    }
}
