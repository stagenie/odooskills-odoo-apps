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
        // Régression sélecteur (Task 6) : créer un 2e dashboard (auto-sélectionné)
        // puis REBASCULER sur le 1er via le <select>. Avec le handler cassé
        // (« v2 is not a function »), l'erreur JS fait échouer le tour ; et si
        // selectDashboard tournait avec un mauvais id, le re-render OWL
        // (t-att-selected => propriété DOM option.selected, cf. isProp owl.js)
        // décocherait la 1re option => :checked est l'assertion d'état correcte
        // ([selected] ne marche PAS : OWL ne pose jamais l'attribut).
        { trigger: ".o_oski_new_dashboard", run: "click" },
        { trigger: ".o_oski_dashboard_select option:nth-child(2):not(:visible)", run: () => {} },
        { trigger: ".o_oski_dashboard_select", run: "selectByIndex 0" },
        { trigger: ".o_oski_dashboard_select option:first-child:checked:not(:visible)", run: () => {} },
    ],
});
