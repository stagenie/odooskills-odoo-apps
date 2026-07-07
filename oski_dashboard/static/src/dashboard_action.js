import { Component, EventBus, useState, useSubEnv, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DashboardGrid } from "./grid/dashboard_grid";
import { WidgetEditorDialog } from "./editor/widget_editor_dialog";

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
        });
        onWillStart(async () => {
            await this.loadDashboards();
        });
    }

    get current() {
        return this.state.dashboards.find((d) => d.id === this.state.currentId) || null;
    }

    async loadDashboards() {
        this.state.dashboards = await this.orm.searchRead(
            "oski.dashboard", [], ["name", "layout_json", "refresh_interval", "user_id"]);
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
        this.state.layout = JSON.parse(this.current.layout_json || "{}");
        this.state.widgets = await this.orm.searchRead(
            "oski.dashboard.widget", [["dashboard_id", "=", dashboardId]],
            ["name", "widget_type", "model_id", "options"]);
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
