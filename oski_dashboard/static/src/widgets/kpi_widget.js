import { Component } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class KpiWidget extends Component {
    static template = "oski_dashboard.KpiWidget";
    static props = { widget: Object, payload: Object };

    get deltaClass() {
        const delta = this.props.payload.delta_pct;
        return delta === null ? "" : delta >= 0 ? "text-success" : "text-danger";
    }
    get formattedTotal() {
        return new Intl.NumberFormat().format(this.props.payload.total || 0);
    }
}

dashboardWidgetRegistry.add("kpi", { component: KpiWidget });
