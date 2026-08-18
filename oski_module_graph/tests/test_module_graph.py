from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

MODULE = "odoo.addons.oski_module_graph.wizards.oski_module_graph"


@tagged("post_install", "-at_install")
class TestModuleGraph(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Graph = cls.env["oski.module.graph"]
        cls.base = cls.env["ir.module.module"].search([("name", "=", "base")], limit=1)
        cls.mine = cls.env["ir.module.module"].search(
            [("name", "=", "oski_module_graph")], limit=1)

    # --- étages -----------------------------------------------------------

    def test_a_module_sits_above_everything_it_needs(self):
        layers = self.Graph._layers({"base": [], "web": ["base"], "sale": ["web", "base"]})
        self.assertEqual(layers[0], ["base"])
        self.assertEqual(layers[1], ["web"])
        self.assertEqual(layers[2], ["sale"])

    def test_the_longest_chain_decides_the_floor(self):
        """``d`` dépend de ``a`` directement et par ``b``/``c`` : c'est la plus
        longue chaîne qui fixe l'étage, sinon une flèche remonterait."""
        layers = self.Graph._layers({"a": [], "b": ["a"], "c": ["b"], "d": ["a", "c"]})
        self.assertEqual(layers[3], ["d"])

    def test_a_cycle_does_not_freeze_the_server(self):
        layers = self.Graph._layers({"a": ["b"], "b": ["a"]})
        self.assertEqual(sum(len(names) for names in layers), 2)

    def test_independent_modules_share_a_floor(self):
        layers = self.Graph._layers({"a": [], "b": [], "c": ["a"]})
        self.assertEqual(layers[0], ["a", "b"])

    # --- périmètre --------------------------------------------------------

    def test_without_following_the_perimeter_stays_closed(self):
        """Aucune flèche ne doit partir vers un nœud absent du dessin."""
        graph = self.Graph._dependency_map(self.mine, follow=False)
        self.assertEqual(set(graph), {"oski_module_graph"})
        self.assertEqual(graph["oski_module_graph"], [])

    def test_following_brings_in_what_is_needed(self):
        graph = self.Graph._dependency_map(self.mine, follow=True)
        self.assertIn("base", graph)
        self.assertIn("base", graph["oski_module_graph"])

    # --- dessin -----------------------------------------------------------

    def test_the_drawing_holds_one_box_per_module(self):
        graph = {"base": [], "web": ["base"]}
        svg = self.Graph._render_svg(graph, self.Graph._layers(graph))
        self.assertEqual(svg.count("<rect"), 2)
        self.assertEqual(svg.count("<path d="), 2, "une flèche, plus la pointe du marqueur")
        self.assertIn("</svg>", svg)

    def test_a_name_is_never_taken_for_markup(self):
        graph = {"<script>alert(1)</script>": []}
        svg = self.Graph._render_svg(graph, self.Graph._layers(graph))
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_a_long_name_is_cut_not_overflowed(self):
        name = "oski_" + "x" * 60
        graph = {name: []}
        svg = self.Graph._render_svg(graph, self.Graph._layers(graph))
        self.assertIn("…", svg)
        self.assertNotIn(name, svg)

    # --- actions ----------------------------------------------------------

    def test_drawing_fills_the_counters(self):
        wizard = self.Graph.create({
            "module_ids": [(6, 0, self.mine.ids)], "with_dependencies": True})
        wizard.action_draw()
        self.assertTrue(wizard.svg)
        self.assertGreaterEqual(wizard.node_count, 2)
        self.assertGreaterEqual(wizard.edge_count, 1)

    def test_an_empty_selection_is_refused(self):
        wizard = self.Graph.create({"module_ids": [(5, 0, 0)]})
        with self.assertRaises(UserError):
            wizard.action_draw()

    def test_too_many_modules_is_refused_rather_than_unreadable(self):
        wizard = self.Graph.create({
            "module_ids": [(6, 0, self.mine.ids)], "with_dependencies": True})
        with patch(MODULE + ".MAX_NODES", 1), self.assertRaises(UserError):
            wizard.action_draw()

    def test_the_button_on_a_module_opens_a_drawn_graph(self):
        action = self.mine.action_oski_module_graph()
        wizard = self.Graph.browse(action["res_id"])
        self.assertTrue(wizard.svg)
        self.assertIn(self.mine, wizard.module_ids)

    def test_the_tool_is_closed_to_ordinary_users(self):
        """``TransactionCase.env`` est superutilisateur : sans ``with_user``,
        aucun droit n'est éprouvé."""
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_graph_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        with self.assertRaises(AccessError):
            self.Graph.with_user(user).create({})
