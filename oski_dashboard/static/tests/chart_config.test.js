import { describe, expect, test } from "@odoo/hoot";
import { buildChartConfig } from "@oski_dashboard/core/chart_config";

describe("oski_dashboard chart config", () => {
    const payload = { labels: ["A", "B"], values: [3, 7], total: 10 };

    test("bar", () => {
        const config = buildChartConfig("bar", payload);
        expect(config.type).toBe("bar");
        expect(config.data.labels).toEqual(["A", "B"]);
        expect(config.data.datasets[0].data).toEqual([3, 7]);
    });

    test("area = line + fill", () => {
        const config = buildChartConfig("area", payload);
        expect(config.type).toBe("line");
        expect(config.data.datasets[0].fill).toBe(true);
    });

    test("donut cutout", () => {
        const config = buildChartConfig("donut", payload);
        expect(config.type).toBe("doughnut");
    });

    test("gauge = doughnut semi + valeur/cible", () => {
        const config = buildChartConfig("gauge", { ...payload }, { target: 20 });
        expect(config.type).toBe("doughnut");
        expect(config.options.circumference).toBe(180);
        expect(config.data.datasets[0].data).toEqual([10, 10]);
    });
});
