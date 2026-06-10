from odoo.tests.common import TransactionCase


class TestOskiAppStore(TransactionCase):

    def _ver(self, name):
        rec = self.env["oski.odoo.version"].search([("name", "=", name)], limit=1)
        if not rec:
            raise ValueError("oski.odoo.version %r absente du référentiel" % name)
        return rec

    def test_category_create(self):
        cat = self.env["oski.module.category"].create({"name": "Ventes"})
        self.assertEqual(cat.name, "Ventes")
        self.assertEqual(cat.sequence, 10)

    def test_version_unique_per_odoo_version(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        module = self.env["oski.module"].create(
            {"name": "Mon Module", "technical_name": "oski_demo"}
        )
        self.env["oski.module.version"].create(
            {"module_id": module.id, "odoo_version_id": self._ver("19.0").id, "module_version": "19.0.1.0.0"}
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["oski.module.version"].create(
                {"module_id": module.id, "odoo_version_id": self._ver("19.0").id, "module_version": "19.0.1.0.1"}
            )
            self.env.flush_all()

    def test_technical_name_unique(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        self.env["oski.module"].create({"name": "A", "technical_name": "oski_a"})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["oski.module"].create({"name": "B", "technical_name": "oski_a"})
            self.env.flush_all()

    def test_website_url_uses_apps_prefix(self):
        module = self.env["oski.module"].create(
            {"name": "Mon Module", "technical_name": "oski_demo2"}
        )
        self.assertTrue(module.website_url.startswith("/apps/"))
        self.assertIn(str(module.id), module.website_url)

    def test_default_not_published(self):
        module = self.env["oski.module"].create(
            {"name": "Brouillon", "technical_name": "oski_draft"}
        )
        self.assertFalse(module.is_published)

    def test_product_reverse_link(self):
        product = self.env["product.template"].create(
            {"name": "Module Demo", "type": "service", "list_price": 0.0}
        )
        module = self.env["oski.module"].create(
            {"name": "Demo", "technical_name": "oski_demo3", "product_tmpl_id": product.id}
        )
        self.assertEqual(product.oski_module_id, module)

    def test_public_sees_only_published(self):
        pub = self.env["oski.module"].create(
            {"name": "Publié", "technical_name": "oski_pub", "is_published": True}
        )
        self.env["oski.module"].create(
            {"name": "Brouillon", "technical_name": "oski_hidden", "is_published": False}
        )
        public_user = self.env.ref("base.public_user")
        visible = self.env["oski.module"].with_user(public_user).search([])
        self.assertIn(pub, visible)
        self.assertTrue(all(m.is_published for m in visible))

    def test_version_lines_order_newest_first(self):
        module = self.env["oski.module"].create(
            {"name": "Order Test", "technical_name": "oski_order_test"}
        )
        for v in ("15.0", "19.0", "17.0"):
            self.env["oski.module.version"].create(
                {
                    "module_id": module.id,
                    "odoo_version_id": self._ver(v).id,
                    "module_version": v + ".1.0.0",
                }
            )
        module.invalidate_recordset()
        self.assertEqual(
            module.version_line_ids.mapped("odoo_version"),
            ["19.0", "17.0", "15.0"],
            "Lignes de version ordonnées plus récente d'abord",
        )
