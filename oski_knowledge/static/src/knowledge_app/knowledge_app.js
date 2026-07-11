import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

const ARTICLE_FIELDS = ["id", "name", "icon", "child_count", "section", "parent_id"];

export class KnowledgeApp extends Component {
    static template = "oski_knowledge.KnowledgeApp";
    static components = { View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            favorites: [],
            workspace: [],
            private: [],
            expanded: {},      // id -> [childNodes]
            currentId: null,
        });
        onWillStart(() => this.reload());
    }

    // --- Chargement (droits utilisateur : aucun sudo, les record rules filtrent) ---
    async reload() {
        const [favRel, roots] = await Promise.all([
            this.orm.searchRead(
                "knowledge.article.favorite", [], ["article_id", "sequence"],
                { order: "sequence, id" }),
            this.orm.searchRead(
                "knowledge.article",
                [["parent_id", "=", false], ["active", "=", true]],
                ARTICLE_FIELDS, { order: "sequence, id" }),
        ]);
        const favIds = favRel.map((f) => f.article_id[0]);
        this.state.favorites = favIds.length
            ? await this.orm.searchRead(
                "knowledge.article", [["id", "in", favIds]], ARTICLE_FIELDS)
            : [];
        this.state.workspace = roots.filter((a) => a.section === "workspace");
        this.state.private = roots.filter((a) => a.section === "private");
        // Recharge les enfants déjà dépliés pour refléter create/move/archive.
        const expandedIds = Object.keys(this.state.expanded).map((k) => parseInt(k, 10));
        for (const id of expandedIds) {
            await this.loadChildren(id);
        }
    }

    async loadChildren(articleId) {
        this.state.expanded[articleId] = await this.orm.searchRead(
            "knowledge.article",
            [["parent_id", "=", articleId], ["active", "=", true]],
            ARTICLE_FIELDS, { order: "sequence, id" });
    }

    isExpanded(articleId) {
        return articleId in this.state.expanded;
    }

    async toggleExpand(node) {
        if (this.isExpanded(node.id)) {
            delete this.state.expanded[node.id];
        } else {
            await this.loadChildren(node.id);
        }
    }

    selectArticle(node) {
        this.state.currentId = node.id;
    }

    isFavorite(node) {
        return this.state.favorites.some((f) => f.id === node.id);
    }

    async toggleFavorite(node) {
        await this.orm.call("knowledge.article", "action_toggle_favorite", [[node.id]]);
        await this.reload();
    }

    async createRoot(section) {
        const id = await this.orm.create("knowledge.article", [{
            name: "Nouvel article", section: section,
        }]);
        await this.reload();
        this.state.currentId = id[0];
    }

    async createChild(parentNode) {
        const id = await this.orm.create("knowledge.article", [{
            name: "Nouvel article", parent_id: parentNode.id,
        }]);
        if (!this.isExpanded(parentNode.id)) {
            await this.loadChildren(parentNode.id);
        } else {
            await this.loadChildren(parentNode.id);
        }
        this.state.currentId = id[0];
    }

    // Props du composant View : form embarqué sur l'article sélectionné.
    // NOTE (adaptation v19, cf. odoo/addons/web/static/src/views/view.js:373 et
    // .../form/form_controller.js:363) : le mode edit/readonly du form dérive
    // de `props.readonly` (lu par form_view.js:25-27), jamais d'un prop `mode`
    // au niveau racine — `FormController.props` est une liste stricte (pas de
    // "*"), donc une clé `mode` inconnue lève `OwlError: Invalid props for
    // component 'FormController': unknown key 'mode'` au montage. `readonly`
    // n'étant pas positionné ici, le form s'ouvre déjà en édition par défaut
    // (form_controller.js:363 : `this.props.readonly ? "readonly" : "edit"`).
    get viewProps() {
        return {
            type: "form",
            resModel: "knowledge.article",
            resId: this.state.currentId,
            display: { controlPanel: false },
        };
    }
}

registry.category("actions").add("oski_knowledge.app", KnowledgeApp);
