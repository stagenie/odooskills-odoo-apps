import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { dashboardWidgetRegistry } from "../core/widget_registry";

export class WidgetShell extends Component {
    static template = "oski_dashboard.WidgetShell";
    static props = {
        widget: Object,
        dashboard: Object,
        editMode: { type: Boolean, optional: true },
        globalFilters: { type: Array, optional: true },
        reloadStamp: { type: Number, optional: true },
        onEdit: { type: Function, optional: true },
        onRemove: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ payload: null, error: null });
        onWillStart(() => this.loadData(this.props));
        onWillUpdateProps((next) => this.loadData(next));
    }

    get widgetComponent() {
        const entry = dashboardWidgetRegistry.get(this.props.widget.widget_type, null);
        return entry ? entry.component : null;
    }

    async loadData(props) {
        try {
            const payload = await this.orm.call(
                "oski.dashboard.widget", "get_widget_data",
                [props.widget.id, props.globalFilters || []]);
            // payload.options est déjà un dict (parsé côté serveur)
            this.state.payload = payload;
            this.state.error = null;
        } catch (error) {
            this.state.error = error.data?.message || String(error);
        }
    }

    // Hook drill-down : no-op par défaut (FREE, pas de drill_level_ids).
    // oski_dashboard_pro (drill.js) patche cette méthode pour descendre d'un
    // niveau (drill_more) ou ouvrir la liste native au dernier niveau —
    // transmis en prop optionnelle aux widgets enfants (cf. template) qui
    // l'appellent en priorité sur le cross-filtering (Task 11) quand le
    // payload indique un drill en cours.
    onSegmentClick(index) {}
}
