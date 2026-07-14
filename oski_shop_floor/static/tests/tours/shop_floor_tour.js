/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("oski_shop_floor_tour", {
    steps: () => [
        { trigger: ".o_sf_workcenter .o_sf_card", run: "click" },
        { trigger: ".o_sf_orders .o_sf_row", run: "click" },
        { trigger: ".o_sf_detail .o_sf_start", run: "click" },
        { trigger: ".o_sf_pause" },  // l'OT est passé en cours
        { trigger: ".o_sf_comp_add", run: "click" },
        { trigger: ".o_sf_finish", run: "click" },
        { trigger: ".o_sf_workcenter, .o_sf_orders" },  // retour après clôture
    ],
});
