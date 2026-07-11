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
        this._trackFetchProps(this.props);
        onWillStart(() => this.loadData(this.props));
        // Le parent (DashboardAction/DashboardGrid) se re-rend pour des
        // raisons sans rapport avec les données du widget (editMode, drag de
        // layout...) : sans garde, onWillUpdateProps re-fetch à CHAQUE
        // re-render parent, un WidgetShell par widget. Ne refetch que si un
        // des trois signaux pertinents change réellement — comparaison par
        // référence, cohérente avec dashboard_action.js qui recrée
        // volontairement un nouveau tableau globalFilters pour signaler un
        // rafraîchissement (refreshWidgets/addFilter/removeFilter).
        onWillUpdateProps((next) => {
            if (next.widget.id === this._fetchWidgetId &&
                next.globalFilters === this._fetchGlobalFilters &&
                next.reloadStamp === this._fetchReloadStamp) {
                return;
            }
            this._trackFetchProps(next);
            return this.loadData(next);
        });
    }

    _trackFetchProps(props) {
        this._fetchWidgetId = props.widget.id;
        this._fetchGlobalFilters = props.globalFilters;
        this._fetchReloadStamp = props.reloadStamp;
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
