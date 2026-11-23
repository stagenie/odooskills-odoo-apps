import { Component, t, useProps } from "@odoo/owl";
import { dashboardWidgetRegistry } from "../core/widget_registry";
import { formatFloat } from "@web/core/utils/numbers";

export class ListWidget extends Component {
    static template = "oski_dashboard.ListWidget";
    props = useProps({
        widget: t.object(), payload: t.object(),
        onSegmentClick: t.function().optional(),
    });

    get rows() {
        const { labels, values } = this.props.payload;
        // Valeurs au format de la langue de l'utilisateur (séparateur de milliers, 2 décimales au plus).
        return labels.map((label, index) => {
            const value = values[index];
            return {
                label,
                value: typeof value === "number"
                    ? formatFloat(value, { digits: [false, 2], trailingZeros: false })
                    : value,
            };
        });
    }

    // No-op par défaut (FREE) : le module pro patche cette méthode pour émettre
    // un filtre cross-widget au clic sur une ligne (cross_filter.js).
    onRowClick(index) {}
}

dashboardWidgetRegistry.add("list", { component: ListWidget });
