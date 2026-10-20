/** @odoo-module **/

import { Component, useProps, t } from "@odoo/owl";

export class ScanBanner extends Component {
    static template = "oski_stock_barcode.ScanBanner";
    props = useProps({
        active: t.boolean().optional(),
        lastScan: t.string().optional(),
        lastScanStatus: t.string().optional(),
        message: t.string().optional(),
    });

    get bannerClass() {
        if (this.props.lastScanStatus === 'success') return 'o_scan_banner o_scan_success';
        if (this.props.lastScanStatus === 'error') return 'o_scan_banner o_scan_error';
        return 'o_scan_banner';
    }

    get displayMessage() {
        return this.props.message || "Scannez un article avec la douchette";
    }
}
