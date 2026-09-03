from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestExportLog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["oski.export.log"]
        cls.partners = cls.env["res.partner"].create([
            {"name": "Export A", "ref": "EA"},
            {"name": "Export B", "ref": "EB"},
        ])
        cls.exporter = cls.env["res.users"].create({
            "name": "Exportateur", "login": "exportateur@example.com",
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("base.group_allow_export").id,
            ])],
        })

    def _logs(self, model_name="res.partner"):
        return self.Log.search([("model_name", "=", model_name)])

    def test_export_leaves_a_trace(self):
        self.partners.with_user(self.exporter).export_data(["name", "ref"])
        log = self._logs()
        self.assertEqual(len(log), 1)
        self.assertEqual(log.user_id, self.exporter)
        self.assertEqual(log.record_count, 2, "Deux contacts exportés, deux lignes comptées.")
        self.assertEqual(log.field_count, 2)
        self.assertIn("ref", log.field_names)
        self.assertEqual(log.model_label, self.env["ir.model"]._get("res.partner").name)

    def test_each_export_is_a_separate_line(self):
        records = self.partners.with_user(self.exporter)
        records.export_data(["name"])
        records.export_data(["ref"])
        self.assertEqual(len(self._logs()), 2)

    def test_refused_export_logs_nothing(self):
        forbidden = self.env["res.users"].create({
            "name": "Sans droit", "login": "sansdroit@example.com",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(UserError):
            self.partners.with_user(forbidden).export_data(["name"])
        self.assertFalse(
            self._logs(),
            "Un export refusé n'a rien fait sortir : il ne doit rien inscrire.",
        )

    def test_empty_selection_is_counted_as_zero(self):
        self.env["res.partner"].with_user(self.exporter).export_data(["name"])
        log = self._logs()
        self.assertEqual(len(log), 1)
        self.assertEqual(log.record_count, 0)

    def test_the_journal_does_not_log_its_own_export(self):
        self.partners.with_user(self.exporter).export_data(["name"])
        self._logs().with_user(self.exporter).export_data(["model_name"])
        self.assertFalse(
            self.Log.search([("model_name", "=", "oski.export.log")]),
            "Exporter le journal ne doit pas produire de ligne de journal.",
        )

    def test_long_field_list_is_truncated(self):
        many = ["name"] * 900
        self.partners.with_user(self.exporter).export_data(many)
        log = self._logs()
        self.assertEqual(log.field_count, 900)
        self.assertLessEqual(len(log.field_names), 2000)
