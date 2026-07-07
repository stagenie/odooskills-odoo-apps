import { Component, EventBus, useState, useSubEnv, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DashboardGrid } from "./grid/dashboard_grid";

export class DashboardAction extends Component {
    static template = "oski_dashboard.DashboardAction";
    static components = { DashboardGrid };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
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
}

registry.category("actions").add("oski_dashboard.action", DashboardAction);
