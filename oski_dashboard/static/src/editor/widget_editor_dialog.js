import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const WIDGET_TYPES = [
    ["kpi", "KPI"], ["bar", "Barres"], ["line", "Lignes"], ["area", "Aires"],
    ["pie", "Camembert"], ["donut", "Donut"], ["list", "Liste"],
    ["gauge", "Jauge"], ["text", "Texte"],
];
const PERIODS = [
    ["all", "Tout"], ["today", "Aujourd'hui"], ["this_week", "Cette semaine"],
    ["this_month", "Ce mois"], ["this_quarter", "Ce trimestre"], ["this_year", "Cette année"],
    ["last_7d", "7 derniers jours"], ["last_30d", "30 derniers jours"],
    ["last_90d", "90 derniers jours"], ["last_12m", "12 derniers mois"],
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
            values: { name: "Nouveau widget", widget_type: "kpi", model_id: false,
                      domain: "[]", group_by_field_id: false, measure_field_id: false,
                      measure_agg: "sum", date_field_id: false, period: "all",
                      compare_previous: false, limit: 0, options: "{}" },
            models: [], fields: [], previewWidget: null,
        });
        onWillStart(async () => {
            this.state.models = await this.orm.searchRead(
                "ir.model", [["transient", "=", false], ["abstract", "=", false]],
                ["model", "name"], { order: "name" });
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
        this.state.fields = await this.orm.searchRead(
            "ir.model.fields",
            [["model_id", "=", this.state.values.model_id], ["store", "=", true]],
            ["name", "field_description", "ttype"], { order: "field_description" });
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
