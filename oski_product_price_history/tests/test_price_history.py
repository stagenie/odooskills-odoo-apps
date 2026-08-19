from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPriceHistory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["product.template"].create({
            "name": "Fenêtre bois-alu", "list_price": 780.0, "type": "consu"})
        cls.product = cls.template.product_variant_id
        cls.history = cls.env["oski.product.price.history"]

    def _rows(self, field_name=None):
        domain = [("product_tmpl_id", "=", self.template.id)]
        if field_name:
            domain.append(("field_name", "=", field_name))
        return self.history.search(domain)

    def test_a_sales_price_change_is_written_down(self):
        self.template.list_price = 820.0
        row = self._rows("list_price")
        self.assertEqual(len(row), 1)
        self.assertEqual(row.old_value, 780.0)
        self.assertEqual(row.new_value, 820.0)
        self.assertEqual(row.user_id, self.env.user)
        self.assertEqual(row.company_id, self.env.company)

    def test_the_gap_is_computed_both_ways(self):
        self.template.list_price = 858.0
        row = self._rows("list_price")
        self.assertEqual(row.variation, 78.0)
        self.assertAlmostEqual(row.variation_percent, 10.0, places=2)

    def test_a_drop_is_written_down_too(self):
        self.template.list_price = 700.0
        row = self._rows("list_price")
        self.assertEqual(row.variation, -80.0)
        self.assertLess(row.variation_percent, 0)

    def test_writing_the_same_price_writes_nothing(self):
        """Un enregistrement sans changement n'est pas un mouvement de prix ;
        l'inscrire noierait l'historique."""
        self.template.list_price = 780.0
        self.assertFalse(self._rows("list_price"))

    def test_writing_another_field_writes_nothing(self):
        self.template.name = "Fenêtre bois-alu 120x140"
        self.assertFalse(self._rows())

    def test_every_change_leaves_its_own_line(self):
        self.template.list_price = 800.0
        self.template.list_price = 850.0
        rows = self._rows("list_price").sorted("id")
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0].old_value, rows[0].new_value), (780.0, 800.0))
        self.assertEqual((rows[1].old_value, rows[1].new_value), (800.0, 850.0))

    def test_a_cost_change_names_its_variant(self):
        self.product.standard_price = 610.0
        row = self._rows("standard_price")
        self.assertEqual(len(row), 1)
        self.assertEqual(row.product_id, self.product)
        self.assertEqual(row.new_value, 610.0)

    def test_a_cost_written_from_the_template_is_caught(self):
        """Le coût posé sur l'article passe par ses variantes : c'est là qu'il
        faut écouter, sinon la moitié des mouvements échappe."""
        self.template.standard_price = 590.0
        row = self._rows("standard_price")
        self.assertEqual(len(row), 1)
        self.assertEqual(row.product_id, self.product)

    def test_the_cost_is_held_company_by_company(self):
        other = self.env["res.company"].create({"name": "Filiale d'essai"})
        self.product.with_company(other).standard_price = 640.0
        row = self._rows("standard_price")
        self.assertEqual(len(row), 1)
        self.assertEqual(row.company_id, other)
        self.assertEqual(row.new_value, 640.0)

    def test_a_variant_keeps_its_own_cost_line(self):
        colour = self.env["product.attribute"].create({"name": "Teinte"})
        values = self.env["product.attribute.value"].create([
            {"name": "Blanc", "attribute_id": colour.id},
            {"name": "Anthracite", "attribute_id": colour.id}])
        self.template.attribute_line_ids = [(0, 0, {
            "attribute_id": colour.id, "value_ids": [(6, 0, values.ids)]})]
        first, second = self.template.product_variant_ids[:2]
        first.standard_price = 600.0
        second.standard_price = 650.0
        rows = self._rows("standard_price")
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows.mapped("product_id").ids),
                         {first.id, second.id})

    def test_the_product_form_counts_and_opens_its_history(self):
        self.template.list_price = 800.0
        self.product.standard_price = 610.0
        self.template.invalidate_recordset()
        self.assertEqual(self.template.oski_price_history_count, 2)
        action = self.template.action_oski_price_history()
        self.assertEqual(action["res_model"], "oski.product.price.history")
        found = self.history.search(action["domain"])
        self.assertEqual(len(found), 2)

    def test_another_product_keeps_its_own_history(self):
        other = self.env["product.template"].create({
            "name": "Porte d'entrée", "list_price": 1200.0, "type": "consu"})
        other.list_price = 1250.0
        self.template.list_price = 800.0
        self.assertEqual(len(self._rows()), 1)
        self.assertEqual(
            len(self.history.search([("product_tmpl_id", "=", other.id)])), 1)

    def test_an_employee_may_read_but_not_rewrite_the_past(self):
        """L'historique n'a de valeur que si personne ne peut le retoucher."""
        self.template.list_price = 800.0
        row = self._rows("list_price")
        employee = self.env["res.users"].create({
            "name": "Employé", "login": "oski_price_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.assertTrue(row.with_user(employee).read(["new_value"]))
        with self.assertRaises(Exception):
            row.with_user(employee).write({"new_value": 1.0})
