import { Component, t, useProps } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class TextWidget extends Component {
    static template = "oski_dashboard.TextWidget";
    props = useProps({
        widget: t.object(), payload: t.object(),
        onSegmentClick: t.function().optional(),
    });
}

dashboardWidgetRegistry.add("text", { component: TextWidget });
