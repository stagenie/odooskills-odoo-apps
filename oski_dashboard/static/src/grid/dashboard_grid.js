import { Component, useRef } from "@odoo/owl";
import { WidgetShell } from "../widgets/widget_shell";
import { useGridDnd } from "./grid_dnd";
import { GRID_COLS, ROW_HEIGHT } from "./grid_constants";

export { GRID_COLS, ROW_HEIGHT };

export class DashboardGrid extends Component {
    static template = "oski_dashboard.DashboardGrid";
    static components = { WidgetShell };
    static props = {
        dashboard: Object,
        widgets: Array,
        layout: Object,
        editMode: { type: Boolean, optional: true },
        globalFilters: { type: Array, optional: true },
        reloadStamp: { type: Number, optional: true },
        onEdit: { type: Function, optional: true },
        onRemove: { type: Function, optional: true },
        onLayoutChange: { type: Function, optional: true },
    };

    setup() {
        this.gridRef = useRef("grid");
        useGridDnd(this.gridRef, {
            isEnabled: () => this.props.editMode,
            getLayout: () => this.props.layout,
            onDrop: (id, pos) => this.props.onLayoutChange && this.props.onLayoutChange(id, pos),
        });
    }

    cellStyle(widget) {
        const pos = this.props.layout[widget.id] || { x: 0, y: 0, w: 4, h: 3 };
        return `grid-column: ${pos.x + 1} / span ${pos.w};` +
               `grid-row: ${pos.y + 1} / span ${pos.h};`;
    }
}
