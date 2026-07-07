import { Component } from "@odoo/owl";
import { WidgetShell } from "../widgets/widget_shell";

export const GRID_COLS = 12;
export const ROW_HEIGHT = 90;

export class DashboardGrid extends Component {
    static template = "oski_dashboard.DashboardGrid";
    static components = { WidgetShell };
    static props = {
        dashboard: Object,
        widgets: Array,
        layout: Object,
        editMode: { type: Boolean, optional: true },
        globalFilters: { type: Array, optional: true },
        onEdit: { type: Function, optional: true },
        onRemove: { type: Function, optional: true },
        onLayoutChange: { type: Function, optional: true },
    };

    cellStyle(widget) {
        const pos = this.props.layout[widget.id] || { x: 0, y: 0, w: 4, h: 3 };
        return `grid-column: ${pos.x + 1} / span ${pos.w};` +
               `grid-row: ${pos.y + 1} / span ${pos.h};`;
    }
}
