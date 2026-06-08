from odoo.tests.common import TransactionCase


class TestRowColorRule(TransactionCase):

    def _make_rule(self, **kw):
        vals = {
            "name": "Sociétés en rouge",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "expression": "is_company == True",
            "decoration": "danger",
        }
        vals.update(kw)
        return self.env["oski.row.color.rule"].create(vals)

    def test_create_generates_inherited_view(self):
        rule = self._make_rule()
        self.assertTrue(rule.view_id, "Une vue héritée doit être générée.")
        self.assertEqual(rule.view_id.model, "res.partner")
        self.assertTrue(rule.view_id.inherit_id, "La vue doit hériter d'une vue liste.")
        self.assertIn("decoration-danger", rule.view_id.arch_db)
        self.assertIn("is_company == True", rule.view_id.arch_db)

    def test_write_updates_view(self):
        rule = self._make_rule()
        rule.write({"decoration": "success", "expression": "id > 0"})
        self.assertIn("decoration-success", rule.view_id.arch_db)
        self.assertIn("id &gt; 0", rule.view_id.arch_db)

    def test_unlink_removes_view(self):
        rule = self._make_rule()
        view = rule.view_id
        rule.unlink()
        self.assertFalse(view.exists(), "La vue générée doit être supprimée avec la règle.")
