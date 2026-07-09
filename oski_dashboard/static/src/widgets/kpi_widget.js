import { Component } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class KpiWidget extends Component {
    static template = "oski_dashboard.KpiWidget";
    static props = {
        widget: Object, payload: Object,
        onSegmentClick: { type: Function, optional: true },
    };

    get deltaClass() {
        const delta = this.props.payload.delta_pct;
        return delta === null ? "" : delta >= 0 ? "text-success" : "text-danger";
    }
    get formattedTotal() {
        return new Intl.NumberFormat().format(this.props.payload.total || 0);
    }
    get thresholdClass() {
        const { total, thresholds } = this.props.payload;
        // Le PRO émet toujours un objet thresholds (truthy), y compris
        // {warning: null, danger: null} quand aucun seuil n'est configuré —
        // sans le second garde, tout KPI tomberait sur text-success.
        if (!thresholds || (thresholds.danger == null && thresholds.warning == null)) return "";
        if (thresholds.danger != null && total <= thresholds.danger) return "text-danger";
        if (thresholds.warning != null && total <= thresholds.warning) return "text-warning";
        return "text-success";
    }
    get targetProgress() {
        return Math.min(100, 100 * this.props.payload.total / this.props.payload.target);
    }
}

dashboardWidgetRegistry.add("kpi", { component: KpiWidget });
