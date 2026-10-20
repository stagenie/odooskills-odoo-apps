/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";

// S'abonne au service barcode du core ; appelle onBarcode(code) à chaque scan.
export function useShopFloorScan(onBarcode) {
    const barcode = useService("barcode");
    const handler = (ev) => onBarcode(ev.detail.barcode);
    barcode.bus.addEventListener("barcode_scanned", handler);
    onWillUnmount(() => barcode.bus.removeEventListener("barcode_scanned", handler));
}
