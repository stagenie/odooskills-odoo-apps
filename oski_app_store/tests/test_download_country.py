"""B0 — le pays de chaque téléchargement servi, sans jamais garder l'IP."""
from unittest.mock import PropertyMock, patch

from odoo.exceptions import AccessError
from odoo.http import GeoIP
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestDownloadCountry(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        cls.v19 = cls.env["oski.odoo.version"].search([("name", "=", "19.0")], limit=1)
        cls.fr = cls.env.ref("base.fr")
        cls.be = cls.env.ref("base.be")
        cls.portal_user = cls.env["res.users"].create({
            "name": "Client Pays",
            "login": "oski_dl_country",
            "password": "oski_dl_country_pwd",
            "email": "country@example.com",
            "country_id": cls.fr.id,
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })

    def _make_module(self, technical_name, is_free=True):
        attachment = self.env["ir.attachment"].create({
            "name": "%s.zip" % technical_name, "raw": b"ZIPDATA",
            "mimetype": "application/zip",
        })
        module = self.env["oski.module"].create({
            "name": technical_name, "technical_name": technical_name,
            "is_free": is_free, "is_published": True,
        })
        version = self.env["oski.module.version"].create({
            "module_id": module.id, "odoo_version_id": self.v19.id,
            "module_version": "19.0.1.0.0", "attachment_id": attachment.id,
        })
        return module, version

    def _logs(self, module):
        return self.env["oski.module.download"].search([("module_id", "=", module.id)])

    def _geoip(self, code):
        return patch.object(GeoIP, "country_code", new_callable=PropertyMock, return_value=code)

    def test_connected_uses_partner_country(self):
        module, version = self._make_module("oski_dl_logged")
        self.authenticate("oski_dl_country", "oski_dl_country_pwd")
        # La géoloc dirait Belgique : le pays du compte l'emporte.
        with self._geoip("BE"):
            resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.content, b"ZIPDATA")
        log = self._logs(module)
        self.assertEqual(len(log), 1)
        self.assertEqual(log.country_id, self.fr)
        self.assertEqual(log.country_source, "partner")
        self.assertEqual(log.partner_id, self.portal_user.partner_id)
        self.assertEqual(log.odoo_version, "19.0")
        self.assertEqual(log.version_id, version)
        self.assertEqual(log.pricing, "free")

    def test_anonymous_with_geoip(self):
        module, version = self._make_module("oski_dl_geoip")
        self.authenticate(None, None)
        with self._geoip("BE"):
            self.url_open("/apps/download/%s" % version.id)
        log = self._logs(module)
        self.assertEqual(len(log), 1)
        self.assertEqual(log.country_id, self.be)
        self.assertEqual(log.country_source, "geoip")
        self.assertFalse(log.partner_id)

    def test_anonymous_without_geoip_is_unknown(self):
        """Sans base GeoLite2, country_code vaut None : pays vide, zip servi."""
        module, version = self._make_module("oski_dl_nogeo")
        self.authenticate(None, None)
        with self._geoip(None):
            resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.status_code, 200)
        log = self._logs(module)
        self.assertEqual(len(log), 1)
        self.assertFalse(log.country_id)
        self.assertEqual(log.country_source, "unknown")

    def test_continent_code_is_unknown(self):
        """GeoIP renvoie un code de continent quand le pays manque : pas un pays."""
        module, version = self._make_module("oski_dl_continent")
        self.authenticate(None, None)
        with self._geoip("EU"):
            self.url_open("/apps/download/%s" % version.id)
        self.assertFalse(self._logs(module).country_id)

    def test_same_session_logged_once(self):
        """Même règle que le compteur : une ligne par session et par version."""
        module, version = self._make_module("oski_dl_twice")
        self.authenticate(None, None)
        with self._geoip("BE"):
            self.url_open("/apps/download/%s" % version.id)
            self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(len(self._logs(module)), 1)
        self.assertEqual(version.download_count, 1)

    def test_refused_download_not_logged(self):
        module, version = self._make_module("oski_dl_paid_refused", is_free=False)
        self.authenticate(None, None)
        self.url_open("/apps/download/%s" % version.id, allow_redirects=False)
        self.assertFalse(self._logs(module))

    def test_paid_purchased_download_logged_as_paid(self):
        module, version = self._make_module("oski_dl_paid_ok", is_free=False)
        product = self.env["product.template"].create({
            "name": "oski_dl_paid_ok", "type": "service", "list_price": 10.0,
            "taxes_id": [(6, 0, [])], "is_published": True,
        })
        module.product_tmpl_id = product
        order = self.env["sale.order"].create({
            "partner_id": self.portal_user.partner_id.id,
            "order_line": [(0, 0, {"product_id": product.product_variant_id.id, "product_uom_qty": 1})],
        })
        order.action_confirm()
        self.assertEqual(order.oski_country_id, self.fr)
        self.authenticate("oski_dl_country", "oski_dl_country_pwd")
        resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.content, b"ZIPDATA")
        log = self._logs(module)
        self.assertEqual(log.pricing, "paid")
        self.assertEqual(log.country_id, self.fr)

    def test_no_ip_stored(self):
        fields = self.env["oski.module.download"]._fields
        self.assertFalse([name for name in fields if "ip" in name.split("_")])

    def test_manager_only(self):
        Download = self.env["oski.module.download"]
        with self.assertRaises(AccessError):
            Download.with_user(self.portal_user).search([])
        employee = self.env["res.users"].create({
            "name": "Employé", "login": "oski_dl_employee",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(AccessError):
            Download.with_user(employee).search([])
        manager = self.env["res.users"].create({
            "name": "Gestionnaire", "login": "oski_dl_manager",
            "group_ids": [(6, 0, [self.env.ref("oski_app_store.group_manager").id])],
        })
        Download.with_user(manager).search([])
        with self.assertRaises(AccessError):
            Download.with_user(manager).create({"module_id": self._make_module("oski_dl_acl")[0].id})
