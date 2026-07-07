import { Component } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class TextWidget extends Component {
    static template = "oski_dashboard.TextWidget";
    static props = { widget: Object, payload: Object };
}

dashboardWidgetRegistry.add("text", { component: TextWidget });
