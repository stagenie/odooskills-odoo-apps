from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOdooVersionRegistry(TransactionCase):
    def test_initial_data_loaded(self):
        versions = self.env["oski.odoo.version"].search([])
        self.assertEqual(
            versions.mapped("name"),
            ["20.0", "19.0", "18.0", "17.0", "16.0", "15.0"],
            "Ordre = sequence desc (plus récente d'abord)",
        )

    def test_get_supported_order(self):
        self.assertEqual(
            self.env["oski.odoo.version"].get_supported(),
            ["20.0", "19.0", "18.0", "17.0", "16.0", "15.0"],
        )

    def test_v20_flagged_upcoming(self):
        """La 20.0 est annoncée mais pas encore sortie : aucune archive."""
        v20 = self.env.ref("oski_app_store.odoo_version_20")
        self.assertTrue(v20.is_upcoming)
        self.assertEqual(self.env["oski.odoo.version"].get_upcoming(), ["20.0"])

    def test_get_released_excludes_upcoming(self):
        self.assertEqual(
            self.env["oski.odoo.version"].get_released(),
            ["19.0", "18.0", "17.0", "16.0", "15.0"],
        )

    def test_get_default_flag(self):
        self.assertEqual(self.env["oski.odoo.version"].get_default(), "19.0")

    def test_get_default_never_upcoming(self):
        """Sans flag, le défaut retombe sur la plus récente version SORTIE."""
        self.env["oski.odoo.version"].search([]).write({"is_default": False})
        self.assertEqual(self.env["oski.odoo.version"].get_default(), "19.0")

    def test_add_v21_no_code(self):
        """Ajouter une version = un simple enregistrement, visible en tête."""
        self.env["oski.odoo.version"].create(
            {"name": "21.0", "sequence": 210, "is_upcoming": True}
        )
        self.assertEqual(
            self.env["oski.odoo.version"].get_supported()[0], "21.0"
        )
        self.assertEqual(
            self.env["oski.odoo.version"].get_default(), "19.0",
            "une version à venir ne devient jamais le défaut du catalogue",
        )

    def test_name_unique(self):
        from psycopg2.errors import UniqueViolation
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.env["oski.odoo.version"].create(
                {"name": "19.0", "sequence": 999}
            )
