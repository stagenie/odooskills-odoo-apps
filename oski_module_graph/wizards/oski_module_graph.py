from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MAX_NODES = 60

NODE_W = 176
NODE_H = 34
GAP_X = 22
GAP_Y = 68
MARGIN = 24


class OskiModuleGraph(models.TransientModel):
    _name = "oski.module.graph"
    _description = "Graphe des dépendances des modules"

    module_ids = fields.Many2many(
        "ir.module.module", string="Modules",
        domain=[("state", "=", "installed")],
        default=lambda self: self._default_modules())
    with_dependencies = fields.Boolean(
        string="Suivre les dépendances", default=True,
        help="Ajoute au dessin tout ce dont les modules choisis dépendent, "
             "de proche en proche.")
    svg = fields.Html(string="Graphe", sanitize=False, readonly=True)
    node_count = fields.Integer(string="Modules dessinés", readonly=True)
    edge_count = fields.Integer(string="Dépendances", readonly=True)

    @api.model
    def _default_modules(self):
        installed = self.env["ir.module.module"].search([("state", "=", "installed")])
        return installed[:MAX_NODES].ids

    # --- graphe -----------------------------------------------------------

    @api.model
    def _dependency_map(self, modules, follow=True):
        """Rend ``{nom: [dépendances]}``, borné au dessin.

        Une dépendance hors du périmètre est écartée du dictionnaire : le
        dessin ne doit jamais porter une flèche vers un nœud absent.
        """
        Module = self.env["ir.module.module"]
        selected = {module.name: module for module in modules}
        if follow:
            frontier = modules
            while frontier:
                names = frontier.mapped("dependencies_id.name")
                missing = [name for name in set(names) if name not in selected]
                if not missing:
                    break
                frontier = Module.search([("name", "in", missing)])
                selected.update({module.name: module for module in frontier})
        graph = {}
        for name, module in selected.items():
            graph[name] = sorted(
                dep for dep in module.dependencies_id.mapped("name") if dep in selected)
        return graph

    @api.model
    def _layers(self, graph):
        """Range chaque module à un étage : celui de sa plus longue chaîne.

        Le calcul se protège des cycles — impossibles entre modules Odoo, mais
        un graphe tronqué ou une base bricolée n'ont pas à figer le serveur.
        """
        depth = {}

        def compute(name, stack):
            if name in depth:
                return depth[name]
            if name in stack:
                return 0
            stack.add(name)
            deps = [dep for dep in graph.get(name, ()) if dep in graph]
            value = 1 + max([compute(dep, stack) for dep in deps], default=-1)
            stack.discard(name)
            depth[name] = value
            return value

        for name in graph:
            compute(name, set())
        layers = []
        for name in sorted(graph, key=lambda item: (depth[item], item)):
            level = depth[name]
            while len(layers) <= level:
                layers.append([])
            layers[level].append(name)
        return layers

    # --- dessin -----------------------------------------------------------

    @api.model
    def _render_svg(self, graph, layers):
        positions = {}
        for level, names in enumerate(layers):
            for column, name in enumerate(names):
                positions[name] = (
                    MARGIN + column * (NODE_W + GAP_X),
                    MARGIN + level * (NODE_H + GAP_Y),
                )
        width = MARGIN * 2 + max(
            [len(names) for names in layers], default=1) * (NODE_W + GAP_X) - GAP_X
        height = MARGIN * 2 + max(len(layers), 1) * (NODE_H + GAP_Y) - GAP_Y

        edges = []
        for name, deps in graph.items():
            x1, y1 = positions[name]
            for dep in deps:
                x2, y2 = positions[dep]
                edges.append(
                    '<path d="M %s %s C %s %s, %s %s, %s %s" fill="none" '
                    'stroke="#9a7d94" stroke-width="1.2" marker-end="url(#oski-arrow)"/>' % (
                        x2 + NODE_W // 2, y2 + NODE_H,
                        x2 + NODE_W // 2, y2 + NODE_H + GAP_Y // 2,
                        x1 + NODE_W // 2, y1 - GAP_Y // 2,
                        x1 + NODE_W // 2, y1))

        nodes = []
        for name, (x, y) in positions.items():
            label = escape(name if len(name) <= 24 else name[:23] + "…")
            nodes.append(
                '<g><rect x="%s" y="%s" rx="6" ry="6" width="%s" height="%s" '
                'fill="#f3eef2" stroke="#764d6a" stroke-width="1.4"/>'
                '<text x="%s" y="%s" text-anchor="middle" font-family="sans-serif" '
                'font-size="13" fill="#3c2438">%s</text></g>' % (
                    x, y, NODE_W, NODE_H, x + NODE_W // 2, y + NODE_H // 2 + 5, label))

        return Markup(
            '<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" '
            'viewBox="0 0 %s %s"><defs><marker id="oski-arrow" viewBox="0 0 10 10" '
            'refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#9a7d94"/></marker></defs>'
            "%s%s</svg>" % (width, height, width, height, "".join(edges), "".join(nodes)))

    # --- actions ----------------------------------------------------------

    def action_draw(self):
        self.ensure_one()
        if not self.module_ids:
            raise UserError(_("Choisissez au moins un module."))
        graph = self._dependency_map(self.module_ids, follow=self.with_dependencies)
        if len(graph) > MAX_NODES:
            raise UserError(_(
                "%(count)s modules à dessiner : au-delà de %(max)s le graphe cesse "
                "d'être lisible. Restreignez la sélection, ou décochez le suivi "
                "des dépendances.", count=len(graph), max=MAX_NODES))
        layers = self._layers(graph)
        self.write({
            "svg": self._render_svg(graph, layers),
            "node_count": len(graph),
            "edge_count": sum(len(deps) for deps in graph.values()),
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
