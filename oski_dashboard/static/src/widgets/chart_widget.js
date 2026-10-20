/* global Chart */
import { Component, onWillStart, onWillUnmount, useRef, useEffect } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { dashboardWidgetRegistry } from "../core/widget_registry";
import { buildChartConfig } from "../core/chart_config";

export class ChartWidget extends Component {
    static template = "oski_dashboard.ChartWidget";
    static props = {
        widget: Object, payload: Object,
        onSegmentClick: { type: Function, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        onWillStart(() => loadBundle("web.chartjs_lib"));
        useEffect(
            () => {
                this.renderChart();
                return () => this.destroyChart();
            },
            () => [this.props.payload]
        );
        onWillUnmount(() => this.destroyChart());
    }

    renderChart() {
        this.destroyChart();
        const config = buildChartConfig(
            this.props.widget.widget_type, this.props.payload, this.props.payload.options);
        if (config && this.canvasRef.el) {
            this.chart = new Chart(this.canvasRef.el, config);
            this.chart.options.onClick = (_ev, elements) => {
                if (elements.length) this.handleSegmentClick(elements[0].index);
            };
        }
    }

    destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    // Hook clic segment : no-op par défaut (FREE). oski_dashboard_pro patche
    // cette méthode en deux couches : cross_filter.js (Task 11, émission de
    // filtre croisé) puis drill.js par-dessus (priorité drill-down si le
    // payload indique un niveau en cours/suivant, sinon super() = filtre
    // croisé).
    handleSegmentClick(index) {}
}

for (const type of ["bar", "line", "area", "pie", "donut", "gauge"]) {
    dashboardWidgetRegistry.add(type, { component: ChartWidget });
}
