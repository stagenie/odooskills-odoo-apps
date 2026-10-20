import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// Odoo 20 : une étape sans action n'a plus de `run` (une fonction vide est
// refusée par le schéma strict de web_tour) ; le déclencheur seul attend l'élément.
registry.category("web_tour.tours").add("oski_dashboard_smoke", {
    url: "/odoo",
    steps: () => [
        { trigger: ".o_oski_dashboard_action .o_oski_new_dashboard", run: "click" },
        { trigger: ".o_oski_dashboard_select option:not(:visible)" },
        { trigger: ".o_oski_toggle_edit.btn-primary" },
        { trigger: ".o_oski_new_dashboard", run: "click" },
        { trigger: ".o_oski_dashboard_select option:nth-child(2):not(:visible)" },
        { trigger: ".o_oski_dashboard_select", run: "selectByIndex 0" },
        { trigger: ".o_oski_dashboard_select option:first-child:checked:not(:visible)" },
        // Favori : l'étoile Material passe en pleine après rechargement (rendu à jour).
        { trigger: ".o_oski_toggle_favorite i.oi[data-icon='star']:not(.oi-filled)" },
        { trigger: ".o_oski_toggle_favorite", run: "click" },
        { trigger: ".o_oski_toggle_favorite i.oi.oi-filled[data-icon='star']" },
        // Plus aucune icône FontAwesome (non chargée en 20 : invisible).
        { trigger: ".o_oski_dashboard_action:not(:has(.fa))" },
    ],
});

registry.category("web_tour.tours").add("oski_dashboard_create_widget", {
    url: "/odoo",
    steps: () => [
        { trigger: ".o_oski_dashboard_action .o_oski_new_dashboard", run: "click" },
        { trigger: ".o_oski_add_widget", run: "click" },
        { trigger: ".o_oski_editor_name", run: "edit KPI Clients" },
        { trigger: ".o_oski_editor_model", run: "selectByLabel Contact" },
        { trigger: ".o_oski_editor_save", run: "click" },
        { trigger: ".o_oski_widget .card-header:contains('KPI Clients')" },
        // Chiffre réellement calculé (pas le sablier de chargement).
        { trigger: ".o_oski_widget .display-5:not(:empty)" },
        // Modification : le dialogue relit le widget, l'en-tête suit le nouveau titre.
        { trigger: ".o_oski_widget_edit", run: "click" },
        { trigger: ".o_oski_editor_name:value('KPI Clients')" },
        { trigger: ".o_oski_editor_name", run: "edit KPI Contacts" },
        { trigger: ".o_oski_editor_save", run: "click" },
        { trigger: ".o_oski_widget .card-header:contains('KPI Contacts')" },
        { trigger: ".o_oski_grid:not(:has(.card-header:contains('KPI Clients')))" },
        // Sortie du mode édition : les boutons d'édition disparaissent.
        { trigger: ".o_oski_toggle_edit", run: "click" },
        { trigger: ".o_oski_toggle_edit.btn-outline-primary" },
        { trigger: ".o_oski_widget:not(:has(.o_oski_widget_edit))" },
        { trigger: ".o_oski_widget .display-5:not(:empty)" },
    ],
});

// Graphique : Chart.js réellement dessiné sur la toile (signal.ref), puis
// redessiné avec les chiffres À JOUR après « Rafraîchir » (pas l'ancien rendu).
function readChartSum() {
    const canvas = document.querySelector(".o_oski_widget canvas");
    const chart = canvas && window.Chart && window.Chart.getChart(canvas);
    return chart ? chart.data.datasets[0].data.reduce((a, b) => a + b, 0) : null;
}

// Attend (5 s max) que la toile porte la somme attendue : le rafraîchissement
// est asynchrone (RPC puis nouveau rendu), une seule lecture serait une course.
async function chartSum(expected) {
    let sum = readChartSum();
    for (let i = 0; i < 50 && sum !== expected; i++) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        sum = readChartSum();
    }
    if (sum === null) {
        throw new Error("Aucun graphique Chart.js sur la toile du widget");
    }
    if (sum !== expected) {
        throw new Error(`Graphique périmé : somme ${sum}, attendu ${expected}`);
    }
}

registry.category("web_tour.tours").add("oski_dashboard_chart", {
    url: "/odoo/action-oski_dashboard.action_oski_dashboard",
    steps: () => [
        { trigger: ".o_oski_widget .card-header:contains('Barres tour')" },
        { trigger: ".o_oski_widget canvas", run: () => chartSum(2) },
        {
            trigger: ".o_oski_refresh",
            run: async () => {
                const [tag] = await rpc("/web/dataset/call_kw/res.partner.category/search", {
                    model: "res.partner.category", method: "search",
                    args: [[["name", "=", "DashTourTag"]]], kwargs: {},
                });
                await rpc("/web/dataset/call_kw/res.partner/create", {
                    model: "res.partner", method: "create",
                    args: [{ name: "Tour P3", category_id: [[4, tag]] }], kwargs: {},
                });
            },
        },
        { trigger: ".o_oski_refresh", run: "click" },
        { trigger: ".o_oski_widget canvas", run: () => chartSum(3) },
    ],
});
