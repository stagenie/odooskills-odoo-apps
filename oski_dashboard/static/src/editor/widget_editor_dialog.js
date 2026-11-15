import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Exporté : le module pro étend la liste via import { WIDGET_TYPES } + push(...)
// — this.WIDGET_TYPES référence CE tableau partagé, les entrées poussées
// apparaissent donc dans le dropdown sans autre câblage.
export const WIDGET_TYPES = [
    ["kpi", "KPI"], ["bar", "Bar"], ["line", "Line"], ["area", "Area"],
    ["pie", "Pie"], ["donut", "Donut"], ["list", "List"],
    ["gauge", "Gauge"], ["text", "Text"],
];
const PERIODS = [
    ["all", "All"], ["today", "Today"], ["this_week", "This Week"],
    ["this_month", "This Month"], ["this_quarter", "This Quarter"], ["this_year", "This Year"],
    ["last_7d", "Last 7 Days"], ["last_30d", "Last 30 Days"],
    ["last_90d", "Last 90 Days"], ["last_12m", "Last 12 Months"],
];

export class WidgetEditorDialog extends Component {
    static template = "oski_dashboard.WidgetEditorDialog";
    static components = { Dialog };
    static props = { dashboardId: Number, widgetId: { type: Number, optional: true },
                     onSaved: Function, close: Function };

    setup() {
        this.orm = useService("orm");
        this.WIDGET_TYPES = WIDGET_TYPES;
        this.PERIODS = PERIODS;
        this.state = useState({
            values: { name: _t("New Widget"), widget_type: "kpi", model_id: false,
                      domain: "[]", group_by_field_id: false, measure_field_id: false,
                      measure_agg: "sum", date_field_id: false, period: "all",
                      compare_previous: false, limit: 0, options: "{}" },
            models: [], fields: [], previewWidget: null,
        });
        onWillStart(async () => {
            // Proxy sudo côté serveur (get_available_models) : ir.model
            // n'est lisible en direct que par group_erp_manager — un
            // searchRead direct ici lève AccessError pour tout utilisateur
            // standard (cf. brief T16-fix B1).
            this.state.models = await this.orm.call(
                "oski.dashboard.widget", "get_available_models", []);
            // Libellés des types et périodes : ceux de la sélection Python, traduits
            // dans la langue de l'utilisateur (types ajoutés par le pro compris).
            const fieldsInfo = await this.orm.call("oski.dashboard.widget", "fields_get",
                [["widget_type", "period"]], { attributes: ["selection"] });
            const typeLabels = Object.fromEntries(fieldsInfo.widget_type?.selection || []);
            const periodLabels = Object.fromEntries(fieldsInfo.period?.selection || []);
            this.WIDGET_TYPES = WIDGET_TYPES.map(([key, label]) => [key, typeLabels[key] || label]);
            this.PERIODS = PERIODS.map(([key, label]) => [key, periodLabels[key] || label]);
            if (this.props.widgetId) {
                const [record] = await this.orm.read("oski.dashboard.widget", [this.props.widgetId],
                    Object.keys(this.state.values));
                for (const key of Object.keys(this.state.values)) {
                    this.state.values[key] = Array.isArray(record[key]) ? record[key][0] : record[key];
                }
                await this.loadFields();
            }
        });
    }

    async loadFields() {
        if (!this.state.values.model_id) {
            this.state.fields = [];
            return;
        }
        // Proxy sudo (get_model_fields) : même raison que get_available_models
        // ci-dessus — ir.model.fields n'est lisible en direct que par
        // group_erp_manager.
        this.state.fields = await this.orm.call(
            "oski.dashboard.widget", "get_model_fields", [this.state.values.model_id]);
    }

    get measureFields() {
        return this.state.fields.filter((f) => ["integer", "float", "monetary"].includes(f.ttype));
    }
    get dateFields() {
        return this.state.fields.filter((f) => ["date", "datetime"].includes(f.ttype));
    }

    async save() {
        const vals = { ...this.state.values, dashboard_id: this.props.dashboardId };
        if (this.props.widgetId) {
            await this.orm.write("oski.dashboard.widget", [this.props.widgetId], vals);
        } else {
            await this.orm.create("oski.dashboard.widget", [vals]);
        }
        this.props.onSaved();
        this.props.close();
    }
}
