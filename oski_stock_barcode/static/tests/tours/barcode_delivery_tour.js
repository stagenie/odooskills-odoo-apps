/** @odoo-module **/

import { registry } from "@web/core/registry";

/** Simule une douchette clavier : frappe rapide des caractères puis Entrée,
 *  captée par le vrai service `barcode` (pas d'appel direct au bus). */
function scan(barcode) {
    const target = document.activeElement || document.body;
    for (const key of [...barcode, "Enter"]) {
        target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    }
}

registry.category("web_tour.tours").add("oski_stock_barcode_delivery_tour", {
    steps: () => [
        {
            content: "Accueil : tuile Expédition",
            trigger: ".o_barcode_card:contains(EXPEDITION)",
            run: "click",
        },
        {
            content: "Choisir le bon du tour",
            trigger: ".o_picking_card:contains(OSKI-TOUR)",
            run: "click",
        },
        {
            content: "Ligne chargée, stock réservé disponible",
            trigger: ".o_barcode_list_count:contains(Total : 0/2)",
        },
        {
            content: "Premier scan",
            trigger: ".o_barcode_table tr:contains(Article tour)",
            run: () => scan("OSKITOUR01"),
        },
        {
            content: "Une unité comptée",
            trigger: ".o_barcode_list_count:contains(Total : 1/2)",
            run: () => scan("OSKITOUR01"),
        },
        {
            content: "Ligne complète",
            trigger: ".o_barcode_table tr.o_line_complete:contains(Article tour)",
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
