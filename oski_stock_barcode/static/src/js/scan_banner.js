/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ScanBanner extends Component {
    static template = "oski_stock_barcode.ScanBanner";
    static props = {
        active: { type: Boolean, optional: true },
        lastScan: { type: String, optional: true },
        lastScanStatus: { type: String, optional: true },
        message: { type: String, optional: true },
    };

    get bannerClass() {
        if (this.props.lastScanStatus === 'success') return 'o_scan_banner o_scan_success';
        if (this.props.lastScanStatus === 'error') return 'o_scan_banner o_scan_error';
        return 'o_scan_banner';
    }

    get displayMessage() {
        return this.props.message || _t("Scan an item with the barcode scanner");
    }
}
