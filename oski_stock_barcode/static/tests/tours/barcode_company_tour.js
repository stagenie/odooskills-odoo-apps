/** @odoo-module **/

import { registry } from "@web/core/registry";

/** Société B seule cochée (cookie `cids`) : la liste n'offre que le bon de B,
 *  et la validation se fait dans B (contexte relayé par barcodeRpc). */
function scan(barcode) {
    const target = document.activeElement || document.body;
    for (const key of [...barcode, "Enter"]) {
        target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    }
}

registry.category("web_tour.tours").add("oski_stock_barcode_company_tour", {
    steps: () => [
        {
            content: "Accueil : tuile Expédition",
            trigger: ".o_barcode_card:contains(EXPEDITION)",
            run: "click",
        },
        {
            content: "Le bon de la société cochée est proposé",
            trigger: ".o_picking_card:contains(OSKI-CO-B)",
        },
        {
            content: "Le bon de la société non cochée n'est pas proposé",
            trigger: "body:not(:has(.o_picking_card:contains(OSKI-CO-A)))",
        },
        {
            content: "Ouvrir le bon de B",
            trigger: ".o_picking_card:contains(OSKI-CO-B)",
            run: "click",
        },
        {
            content: "Scan",
            trigger: ".o_barcode_table tr:contains(Article tour société)",
            run: () => scan("OSKITOURCO"),
        },
        {
            content: "Ligne complète",
            trigger: ".o_barcode_table tr.o_line_complete:contains(Article tour société)",
        },
        {
            content: "Valider la livraison",
            trigger: ".o_barcode_btn.o_btn_primary:contains(Valider la livraison):enabled",
            run: "click",
        },
        {
            content: "Livraison validée",
            trigger: ".o_barcode_validated:contains(Livraison validée)",
        },
    ],
});
