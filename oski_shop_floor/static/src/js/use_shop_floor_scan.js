/** @odoo-module **/

import { usePlugin } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { BarcodePlugin } from "@barcodes/barcode_plugin";

// Odoo 20 : le service « barcode » est devenu BarcodePlugin
// (barcodes/static/src/barcode_plugin.js) ; useService("barcode") n'est
// plus qu'un pont provisoire (« @todo owl3 migration »).
export function useShopFloorScan(onBarcode) {
    const barcode = usePlugin(BarcodePlugin);
    useBus(barcode.bus, "barcode_scanned", (ev) => onBarcode(ev.detail.barcode));
}
