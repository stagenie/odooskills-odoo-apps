/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("oski_shop_floor_tour", {
    steps: () => [
        // Cibler le poste et l'OT créés par le test : la base de test peut
        // contenir des postes de démo (le premier poste n'est pas le nôtre).
        { trigger: ".o_sf_workcenter .o_sf_card:contains('Poste Tour SF')", run: "click" },
        { trigger: ".o_sf_orders .o_sf_row:contains('Fini Tour SF')", run: "click" },
        { trigger: ".o_sf_detail .o_sf_start", run: "click" },
        { trigger: ".o_sf_pause" },  // l'OT est passé en cours
        { trigger: ".o_sf_comp_row:contains('Composant Tour SF') .o_sf_comp_add", run: "click" },
        { trigger: ".o_sf_comp_qty:contains('1 / 1')" },
        // Pause puis reprise : la consommation déjà saisie est conservée.
        { trigger: ".o_sf_pause", run: "click" },
        { trigger: ".o_sf_start", run: "click" },
        { trigger: ".o_sf_pause" },
        {
            // Douchette : frappes clavier sur le document, captées par le
            // BarcodePlugin (Odoo 20) puis par useShopFloorScan.
            trigger: ".o_sf_comp_qty:contains('1 / 1')",
            run() {
                for (const key of [..."TOURCOMP", "Enter"]) {
                    document.body.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
                }
            },
        },
        { trigger: ".o_sf_comp_qty:contains('2 / 1')" },
        { trigger: ".o_sf_finish", run: "click" },
        { trigger: ".o_sf_workcenter, .o_sf_orders" },  // retour après clôture
    ],
});
