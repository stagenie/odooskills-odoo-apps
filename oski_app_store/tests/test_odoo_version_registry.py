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

    def test_v20_released_and_nothing_upcoming(self):
        """Odoo 20 est sortie (2026-10) : plus aucune version « à venir » au référentiel."""
        v20 = self.env.ref("oski_app_store.odoo_version_20")
        self.assertFalse(v20.is_upcoming)
        self.assertEqual(self.env["oski.odoo.version"].get_upcoming(), [])

    def test_get_released_excludes_upcoming(self):
        Version = self.env["oski.odoo.version"]
        self.assertEqual(Version.get_released(), ["20.0", "19.0", "18.0", "17.0", "16.0", "15.0"])
        Version.create({"name": "21.0", "sequence": 210, "is_upcoming": True})
        self.assertNotIn("21.0", Version.get_released())

    def test_get_default_flag(self):
        """Odoo 20 sortie (2026-10) : le catalogue s'ouvre dessus."""
        self.assertEqual(self.env["oski.odoo.version"].get_default(), "20.0")

    def test_get_default_never_upcoming(self):
        """Sans flag, le défaut retombe sur la plus récente version SORTIE (et suivie)."""
        Version = self.env["oski.odoo.version"]
        Version.search([]).write({"is_default": False})
        self.assertEqual(Version.get_default(), "20.0")
        Version.create({"name": "21.0", "sequence": 210, "is_upcoming": True})
        self.assertEqual(Version.get_default(), "20.0")

    def test_add_v21_no_code(self):
        """Ajouter une version = un simple enregistrement, visible en tête."""
        self.env["oski.odoo.version"].create(
            {"name": "21.0", "sequence": 210, "is_upcoming": True}
        )
        self.assertEqual(
            self.env["oski.odoo.version"].get_supported()[0], "21.0"
        )
        self.assertEqual(
            self.env["oski.odoo.version"].get_default(), "20.0",
            "une version à venir SANS drapeau ne devient jamais le défaut du catalogue",
        )

    def test_name_unique(self):
        from psycopg2.errors import UniqueViolation
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.env["oski.odoo.version"].create(
                {"name": "19.0", "sequence": 999}
            )
