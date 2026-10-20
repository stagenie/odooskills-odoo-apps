import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

// Parcours de fumée : appli → kanban (gabarit « card ») → liste → nouveau
// ticket → numéro HT/ attribué à l'enregistrement.
registry.category("web_tour.tours").add("oski_helpdesk_smoke", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="oski_helpdesk.menu_helpdesk_root"]',
            run: "click",
        },
        { trigger: ".o_kanban_view .o_kanban_record:contains(Ticket du parcours)" },
        { trigger: ".o_switch_view.o_list", run: "click" },
        { trigger: ".o_list_view .o_data_row:contains(Ticket du parcours)" },
        { trigger: ".o_list_button_add", run: "click" },
        { trigger: ".o_field_widget[name='name'] input", run: "edit Imprimante en panne" },
        { trigger: ".o_field_widget[name='team_id'] input", run: "edit Équipe parcours" },
        {
            trigger: ".o-autocomplete--dropdown-item .dropdown-item:contains(Équipe parcours)",
            run: "click",
        },
        { trigger: ".o_form_button_save", run: "click" },
        { trigger: ".o_form_saved .o_field_widget[name='number']:contains(HT/)" },
    ],
});
