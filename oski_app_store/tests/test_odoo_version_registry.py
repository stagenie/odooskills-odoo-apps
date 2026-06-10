from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOdooVersionRegistry(TransactionCase):
    def test_initial_data_loaded(self):
        versions = self.env["oski.odoo.version"].search([])
        self.assertEqual(
            versions.mapped("name"), ["19.0", "18.0", "17.0", "16.0", "15.0"],
            "Ordre = sequence desc (plus récente d'abord)",
        )

    def test_get_supported_order(self):
        self.assertEqual(
            self.env["oski.odoo.version"].get_supported(),
            ["19.0", "18.0", "17.0", "16.0", "15.0"],
        )

    def test_get_default_flag(self):
        self.assertEqual(self.env["oski.odoo.version"].get_default(), "19.0")

    def test_get_default_fallback_highest_sequence(self):
        self.env["oski.odoo.version"].search([]).write({"is_default": False})
        self.assertEqual(self.env["oski.odoo.version"].get_default(), "19.0")

    def test_add_v20_no_code(self):
        """Ajouter la v20 = un simple enregistrement, visible en tête."""
        self.env["oski.odoo.version"].create(
            {"name": "20.0", "sequence": 200}
        )
        self.assertEqual(
            self.env["oski.odoo.version"].get_supported()[0], "20.0"
        )

    def test_name_unique(self):
        from psycopg2.errors import UniqueViolation
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.env["oski.odoo.version"].create(
                {"name": "19.0", "sequence": 999}
            )
