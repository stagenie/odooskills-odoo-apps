import { Component, t, useProps } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class ListWidget extends Component {
    static template = "oski_dashboard.ListWidget";
    props = useProps({
        widget: t.object(), payload: t.object(),
        onSegmentClick: t.function().optional(),
    });

    get rows() {
        const { labels, values } = this.props.payload;
        return labels.map((label, index) => ({ label, value: values[index] }));
    }

    // No-op par défaut (FREE) : le module pro patche cette méthode pour émettre
    // un filtre cross-widget au clic sur une ligne (cross_filter.js).
    onRowClick(index) {}
}

dashboardWidgetRegistry.add("list", { component: ListWidget });
