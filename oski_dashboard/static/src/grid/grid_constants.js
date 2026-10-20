// Constantes partagées entre dashboard_grid.js et grid_dnd.js, isolées dans
// ce module dédié : dashboard_grid.js importe useGridDnd (grid_dnd.js) et
// grid_dnd.js a besoin de GRID_COLS/ROW_HEIGHT — les faire transiter par
// dashboard_grid.js créerait un cycle d'import ES module que le loader
// Odoo (contrairement à un bundler) refuse de résoudre au runtime
// ("dependency cycle" -> modules jamais chargés, page blanche).
export const GRID_COLS = 12;
export const ROW_HEIGHT = 90;
