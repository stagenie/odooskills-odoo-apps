import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("oski_knowledge_smoke", {
    url: "/odoo",
    steps: () => [
        // Le module "mail" (dépendance) fournit sa propre appli (Discuss) qui
        // devient la home action par défaut de /odoo → passer par la grille
        // des applis plutôt que supposer un accès direct.
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="oski_knowledge.menu_knowledge_root"]',
            run: "click",
        },
        // Odoo 20 : une étape sans action n'a plus de `run` (fonction vide refusée
        // par le schéma strict de web_tour) ; le déclencheur seul attend l'élément.
        { trigger: ".o_knowledge_app" },
        // Créer un article racine dans l'espace de travail.
        { trigger: ".o_knowledge_new_workspace", run: "click" },
        // Le form embarqué est monté sur le nouvel article : le champ titre est éditable.
        { trigger: ".o_knowledge_main .o_field_widget[name='name'] input", run: "edit Guide interne" },
        // Basculer le favori via l'étoile de la sidebar (action serveur par id ;
        // persiste indépendamment de l'enregistrement du titre).
        { trigger: ".o_knowledge_node.o_knowledge_selected .o_knowledge_fav_toggle", run: "click" },
        // L'article apparaît dans le bloc Favoris ; l'étoile Material passe en pleine.
        { trigger: ".o_knowledge_favorites .o_knowledge_node" },
        { trigger: ".o_knowledge_node.o_knowledge_selected .o_knowledge_fav_toggle i.oi.oi-filled[data-icon='star']" },
        // Sous-article : créé sous l'article courant, le parent se déplie (t-call récursif
        // à paramètre en attribut : un `t-set` dans le corps n'arriverait plus en 20).
        { trigger: ".o_knowledge_workspace .o_knowledge_node.o_knowledge_selected .o_knowledge_new_child", run: "click" },
        { trigger: ".o_knowledge_workspace .o_knowledge_children .o_knowledge_node.o_knowledge_selected" },
        { trigger: ".o_knowledge_main .o_field_widget[name='name'] input", run: "edit Sous-guide" },
        // Plus aucune icône FontAwesome (non chargée en 20 : invisible).
        { trigger: ".o_knowledge_app:not(:has(.fa))" },
    ],
});
