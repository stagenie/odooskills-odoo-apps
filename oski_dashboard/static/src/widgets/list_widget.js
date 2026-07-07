import { Component } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class ListWidget extends Component {
    static template = "oski_dashboard.ListWidget";
    static props = { widget: Object, payload: Object };

    get rows() {
        const { labels, values } = this.props.payload;
        return labels.map((label, index) => ({ label, value: values[index] }));
    }
}

dashboardWidgetRegistry.add("list", { component: ListWidget });
