import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("oski_dashboard_smoke", {
    url: "/odoo",
    steps: () => [
        // Dans la base de test dédiée (seul module « métier » installé), /odoo
        // redirige directement sur l'unique app (pas de grille .o_app à cliquer) :
        // on démarre donc directement sur l'action DashboardAction.
        { trigger: ".o_oski_dashboard_action .o_oski_new_dashboard", run: "click" },
        // <option> n'est jamais jQuery-:visible (pas de boîte de rendu propre) :
        // :not(:visible) évite un TIMEOUT sur ce simple test de présence.
        { trigger: ".o_oski_dashboard_select option:not(:visible)", run: () => {} },
        { trigger: ".o_oski_toggle_edit.btn-primary", run: () => {} },
    ],
});
