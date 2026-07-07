import { onMounted, onWillUnmount } from "@odoo/owl";
import { GRID_COLS, ROW_HEIGHT } from "./grid_constants";

export function useGridDnd(gridRef, { isEnabled, getLayout, onDrop }) {
    let dragState = null;

    function cellFromEvent(gridEl, ev) {
        const rect = gridEl.getBoundingClientRect();
        const colWidth = rect.width / GRID_COLS;
        return {
            x: Math.max(0, Math.min(GRID_COLS - 1, Math.floor((ev.clientX - rect.left) / colWidth))),
            y: Math.max(0, Math.floor((ev.clientY - rect.top) / ROW_HEIGHT)),
        };
    }

    function onPointerDown(ev) {
        if (!isEnabled()) return;
        const cell = ev.target.closest(".o_oski_grid_cell");
        if (!cell) return;
        const widgetId = cell.dataset.widgetId;
        const layout = getLayout();
        const pos = layout[widgetId] || { x: 0, y: 0, w: 4, h: 3 };
        const isResize = ev.target.classList.contains("o_oski_resize_handle");
        dragState = { widgetId, start: { ...pos }, isResize, origin: cellFromEvent(ev.currentTarget, ev) };
        ev.preventDefault();
    }

    function onPointerMove(ev) {
        if (!dragState) return;
        const gridEl = ev.currentTarget;
        const cell = cellFromEvent(gridEl, ev);
        const deltaX = cell.x - dragState.origin.x;
        const deltaY = cell.y - dragState.origin.y;
        const pos = { ...dragState.start };
        if (dragState.isResize) {
            pos.w = Math.max(2, Math.min(GRID_COLS - pos.x, dragState.start.w + deltaX));
            pos.h = Math.max(1, dragState.start.h + deltaY);
        } else {
            pos.x = Math.max(0, Math.min(GRID_COLS - pos.w, dragState.start.x + deltaX));
            pos.y = Math.max(0, dragState.start.y + deltaY);
        }
        dragState.current = pos;
        const cellEl = gridEl.querySelector(`[data-widget-id="${dragState.widgetId}"]`);
        cellEl.style.gridColumn = `${pos.x + 1} / span ${pos.w}`;
        cellEl.style.gridRow = `${pos.y + 1} / span ${pos.h}`;
    }

    function onPointerUp() {
        if (dragState && dragState.current) {
            onDrop(dragState.widgetId, dragState.current);
        }
        dragState = null;
    }

    onMounted(() => {
        const el = gridRef.el;
        el.addEventListener("pointerdown", onPointerDown);
        el.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
    });
    onWillUnmount(() => {
        window.removeEventListener("pointerup", onPointerUp);
    });
}
