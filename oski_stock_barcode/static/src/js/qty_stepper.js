/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class QtyStepper extends Component {
    static template = "oski_stock_barcode.QtyStepper";
    static props = {
        value: Number,
        onChange: Function,
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({ pressing: false });
        this._interval = null;
    }

    get minVal() {
        return this.props.min !== undefined ? this.props.min : 0;
    }

    _increment() {
        const next = this.props.value + 1;
        if (this.props.max !== undefined && next > this.props.max) return;
        this.props.onChange(next);
    }

    _decrement() {
        const next = this.props.value - 1;
        if (next < this.minVal) return;
        this.props.onChange(next);
    }

    _onInputChange(ev) {
        let val = parseInt(ev.target.value, 10);
        if (isNaN(val)) val = this.minVal;
        if (val < this.minVal) val = this.minVal;
        if (this.props.max !== undefined && val > this.props.max) val = this.props.max;
        this.props.onChange(val);
    }

    _startRepeat(fn) {
        this.state.pressing = true;
        fn.call(this);
        this._timeout = setTimeout(() => {
            this._interval = setInterval(() => fn.call(this), 150);
        }, 500);
    }

    _stopRepeat() {
        this.state.pressing = false;
        clearTimeout(this._timeout);
        clearInterval(this._interval);
        this._timeout = null;
        this._interval = null;
    }

    _onMinusDown(ev) {
        ev.preventDefault();
        this._startRepeat(this._decrement);
    }

    _onPlusDown(ev) {
        ev.preventDefault();
        this._startRepeat(this._increment);
    }

    _onPointerUp() {
        this._stopRepeat();
    }
}
