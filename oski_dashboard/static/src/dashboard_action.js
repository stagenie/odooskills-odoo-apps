import { Component, EventBus, useState, useSubEnv, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { DashboardGrid } from "./grid/dashboard_grid";
import { WidgetEditorDialog } from "./editor/widget_editor_dialog";

// Champs lus par selectDashboard() sur oski.dashboard.widget. Exporté : le
// module pro pousse filter_emit/filter_listen dans CE tableau partagé — même
// pattern que WIDGET_TYPES (widget_editor_dialog.js).
export const WIDGET_FIELDS = ["name", "widget_type", "model_id", "model_name",
    "group_by_field_id", "group_by_field_name", "options"];

export class DashboardAction extends Component {
    static template = "oski_dashboard.DashboardAction";
    static components = { DashboardGrid };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        // Sérialise les écritures save_layout : sans file d'attente, deux
        // drags rapprochés peuvent voir leurs RPC arriver dans le désordre
        // et l'ancien layout écraser le nouveau côté serveur.
        this._layoutSaveChain = Promise.resolve();
        useSubEnv({ dashboardBus: new EventBus() });
        this.state = useState({
            dashboards: [], currentId: null, widgets: [], layout: {},
            editMode: false, globalFilters: [],
            // Estampille de (re)chargement du dashboard : incrémentée par
            // selectDashboard() uniquement (PAS par refreshWidgets). Les
            // WidgetShell étant réutilisés par OWL (t-key = widget.id), c'est
            // le signal qui permet aux extensions (drill-down pro) d'invalider
            // leur état client (ex. drillPath) quand le dashboard est
            // rechargé/changé — comme globalFilters est déjà remis à zéro.
            reloadStamp: 0,
        });
        // Écouteur cross-filtering : inerte tant que rien n'émet FILTER-ADD
        // (module pro absent) — le bus existe toujours (useSubEnv ci-dessus).
        this._onFilterAdd = (ev) => this.addFilter(ev.detail);
        this.env.dashboardBus.addEventListener("FILTER-ADD", this._onFilterAdd);
        onWillStart(async () => {
            await this.loadDashboards();
        });
        this.isDestroyed = false;
        onWillUnmount(() => {
            this.isDestroyed = true;
            clearInterval(this.refreshTimer);
            this.env.dashboardBus.removeEventListener("FILTER-ADD", this._onFilterAdd);
        });
    }

    get current() {
        return this.state.dashboards.find((d) => d.id === this.state.currentId) || null;
    }

    get isFavorite() {
        return !!this.current && this.current.favorite_user_ids.includes(user.userId);
    }

    async loadDashboards() {
        this.state.dashboards = await this.orm.searchRead(
            "oski.dashboard", [],
            ["name", "layout_json", "refresh_interval", "user_id", "favorite_user_ids", "sequence"]);
        const userId = user.userId;
        this.state.dashboards.sort((a, b) =>
            (b.favorite_user_ids.includes(userId) - a.favorite_user_ids.includes(userId)) ||
            a.sequence - b.sequence || a.id - b.id);
        if (this.state.dashboards.length) {
            await this.selectDashboard(this.state.dashboards[0].id);
        }
    }

    onSelectChange(ev) {
        return this.selectDashboard(parseInt(ev.target.value, 10));
    }

    async selectDashboard(dashboardId) {
        this.state.currentId = dashboardId;
        this.state.globalFilters = [];
        this.state.reloadStamp++;
        this.state.layout = JSON.parse(this.current.layout_json || "{}");
        this.state.widgets = await this.orm.searchRead(
            "oski.dashboard.widget", [["dashboard_id", "=", dashboardId]],
            WIDGET_FIELDS);
        this.startAutoRefresh();
    }

    addFilter(gf) {
        // Dédup par (model, field, value) : deux widgets de modèles différents
        // groupés par un champ homonyme (ex. sale.state / purchase.state)
        // doivent pouvoir coexister comme filtres distincts.
        const exists = this.state.globalFilters.some(
            (f) => f.model === gf.model && f.field === gf.field && f.value === gf.value);
        if (!exists) {
            this.state.globalFilters = [...this.state.globalFilters, gf];
        }
    }

    removeFilter(index) {
        this.state.globalFilters = this.state.globalFilters.filter((_f, i) => i !== index);
    }

    startAutoRefresh() {
        clearInterval(this.refreshTimer);
        if (this.isDestroyed) {
            return; // selectDashboard résolu après unmount : ne pas relancer de timer
        }
        const seconds = this.current?.refresh_interval || 0;
        if (seconds > 0) {
            this.refreshTimer = setInterval(() => this.refreshWidgets(), seconds * 1000);
        }
    }

    refreshWidgets() {
        this.state.globalFilters = [...this.state.globalFilters]; // force re-fetch (props change)
    }

    async toggleFavorite() {
        await this.orm.call("oski.dashboard", "write", [[this.state.currentId], {
            favorite_user_ids: [[this.isFavorite ? 3 : 4, user.userId]],
        }]);
        await this.loadDashboards();
    }

    toggleEdit() {
        this.state.editMode = !this.state.editMode;
    }

    async createDashboard() {
        const id = await this.orm.create("oski.dashboard", [{ name: "Nouveau dashboard" }]);
        await this.loadDashboards();
        await this.selectDashboard(id[0]);
        this.state.editMode = true;
    }

    async onLayoutChange(widgetId, pos) {
        this.state.layout = { ...this.state.layout, [widgetId]: pos };
        const dashboardId = this.state.currentId;
        // Le layout est stringifié DANS le thunk mis en file : chaque écriture
        // envoie l'état le plus frais et les RPC s'exécutent dans l'ordre.
        // Le .catch garde la chaîne vivante après un RPC en échec — et comme
        // un catch attaché SUPPRIME le dialogue d'erreur global d'Odoo v19
        // (déclenché uniquement par le listener unhandledrejection de
        // error_service), on notifie explicitement l'utilisateur.
        this._layoutSaveChain = this._layoutSaveChain.then(() => {
            if (this.state.currentId !== dashboardId) {
                return; // dashboard changé entre-temps : ne pas écraser l'autre layout
            }
            return this.orm.call("oski.dashboard", "save_layout",
                [dashboardId, JSON.stringify(this.state.layout)]);
        }).catch(() => {
            this.notification.add(
                "Échec de l'enregistrement de la disposition — vos derniers déplacements ne sont pas sauvegardés.",
                { type: "warning" });
        });
    }

    addWidget() {
        this.dialog.add(WidgetEditorDialog, {
            dashboardId: this.state.currentId,
            onSaved: () => this.selectDashboard(this.state.currentId),
        });
    }

    editWidget(widget) {
        this.dialog.add(WidgetEditorDialog, {
            dashboardId: this.state.currentId, widgetId: widget.id,
            onSaved: () => this.selectDashboard(this.state.currentId),
        });
    }

    async removeWidget(widget) {
        await this.orm.unlink("oski.dashboard.widget", [widget.id]);
        await this.selectDashboard(this.state.currentId);
    }
}

registry.category("actions").add("oski_dashboard.action", DashboardAction);
