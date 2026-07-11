const PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                 "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"];

export function buildChartConfig(widgetType, payload, options = {}) {
    const { labels = [], values = [], total = 0 } = payload;
    const colors = labels.map((_, index) => PALETTE[index % PALETTE.length]);
    const base = {
        data: {
            labels,
            datasets: [{ label: options.label || "", data: values }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: ["pie", "donut"].includes(widgetType) } },
        },
    };
    switch (widgetType) {
        case "bar":
            return { ...base, type: "bar",
                     data: { ...base.data, datasets: [{ ...base.data.datasets[0], backgroundColor: colors }] } };
        case "line":
            return { ...base, type: "line",
                     data: { ...base.data, datasets: [{ ...base.data.datasets[0], borderColor: PALETTE[0], tension: 0.3 }] } };
        case "area":
            return { ...base, type: "line",
                     data: { ...base.data, datasets: [{ ...base.data.datasets[0], borderColor: PALETTE[0], backgroundColor: PALETTE[0] + "33", fill: true, tension: 0.3 }] } };
        case "pie":
            return { ...base, type: "pie",
                     data: { ...base.data, datasets: [{ ...base.data.datasets[0], backgroundColor: colors }] } };
        case "donut":
            return { ...base, type: "doughnut",
                     data: { ...base.data, datasets: [{ ...base.data.datasets[0], backgroundColor: colors }] } };
        case "gauge": {
            // ?? (pas ||) : un objectif explicitement configuré à 0 doit
            // rester 0, pas être écrasé par total/1 (0 est une valeur
            // falsy en JS mais un objectif légitime).
            const target = options.target ?? total ?? 1;
            const done = Math.min(total, target);
            return {
                type: "doughnut",
                data: { labels: ["Réalisé", "Restant"],
                        datasets: [{ data: [done, Math.max(target - done, 0)],
                                     backgroundColor: [PALETTE[2], "#e9ecef"] }] },
                options: { responsive: true, maintainAspectRatio: false,
                           rotation: -90, circumference: 180,
                           plugins: { legend: { display: false } } },
            };
        }
        default:
            return null;
    }
}
