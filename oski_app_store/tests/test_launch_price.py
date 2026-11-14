"""Prix de lancement : la liste de prix du site fixe le prix payé, la fiche l'affiche."""
import html
from datetime import datetime

from odoo import Command
from odoo.tests import freeze_time, tagged
from odoo.tests.common import HttpCase

from .common_i18n import activate_french

BEFORE_END = "2026-11-20 10:00:00"
AFTER_END = "2027-01-02 10:00:00"


@tagged("post_install", "-at_install")
class TestLaunchPrice(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        # Même état que la prod avant prep_120 : aucune autre liste de prix.
        cls.env["product.pricelist"].search([]).action_archive()
        cls.website = cls.env["website"].get_current_website()
        cls.currency = cls.website.company_id.currency_id
        cls.categ = cls.env["product.category"].create({"name": "Modules Odoo (test)"})
        cls.product = cls.env["product.template"].create({
            "name": "oski_launch_demo", "type": "service", "list_price": 100.0,
            "categ_id": cls.categ.id, "taxes_id": [(6, 0, [])],
            "is_published": True, "sale_ok": True,
        })
        attachment = cls.env["ir.attachment"].create({
            "name": "oski_launch_demo.zip", "raw": b"ZIPDATA",
            "mimetype": "application/zip",
        })
        cls.module = cls.env["oski.module"].create({
            "name": "oski_launch_demo", "technical_name": "oski_launch_demo",
            "is_free": False, "is_published": True, "price": 100.0,
            "currency_id": cls.currency.id, "product_tmpl_id": cls.product.id,
        })
        cls.env["oski.module.version"].create({
            "module_id": cls.module.id,
            "odoo_version_id": cls.env["oski.odoo.version"].search([("name", "=", "19.0")], limit=1).id,
            "module_version": "19.0.1.0.0", "attachment_id": attachment.id,
        })

    def _launch_pricelist(self):
        """Ce que fait prep_120 : groupe activé + liste −30 % jusqu'au 31/12/2026."""
        group = self.env.ref("product.group_product_pricelist")
        self.env.ref("base.group_user").write({"implied_ids": [Command.link(group.id)]})
        return self.env["product.pricelist"].create({
            "name": "Launch 2026", "currency_id": self.currency.id,
            "website_id": self.website.id, "selectable": False, "sequence": 1,
            "item_ids": [Command.create({
                "applied_on": "2_product_category", "categ_id": self.categ.id,
                "compute_price": "percentage", "percent_price": 30.0,
                "date_end": datetime(2026, 12, 31, 23, 59, 59),
            })],
        })

    def _cart_line(self):
        return self.env["sale.order.line"].search(
            [("product_id.product_tmpl_id", "=", self.product.id)], order="id desc", limit=1
        )

    @freeze_time(BEFORE_END, tick=True)
    def test_page_shows_launch_price(self):
        self._launch_pricelist()
        self.authenticate(None, None)
        body = self.url_open(self.module.website_url).text
        self.assertIn("oski-price-offer", body)
        self.assertIn("<del", body)
        self.assertIn("100.00", body)
        self.assertIn("70.00", body)
        self.assertIn("Launch price — 30% off until December 31, 2026", body)

    @freeze_time(BEFORE_END, tick=True)
    def test_page_launch_price_in_french(self):
        self._launch_pricelist()
        activate_french(self.env)
        self.authenticate(None, None)
        body = html.unescape(self.url_open("/fr" + self.module.website_url).text)
        self.assertIn("Prix de lancement — −30 % jusqu'au 31 décembre 2026", body)

    @freeze_time(BEFORE_END, tick=True)
    def test_page_unchanged_without_pricelist(self):
        self.authenticate(None, None)
        body = self.url_open(self.module.website_url).text
        self.assertNotIn("oski-price-offer", body)
        self.assertNotIn("Launch price", body)
        self.assertIn("oski-btn-buy", body)
        self.assertIn("100.00", body)

    @freeze_time(BEFORE_END, tick=True)
    def test_cart_bills_launch_price(self):
        self._launch_pricelist()
        self.authenticate(None, None)
        self.url_open("/apps/buy/%s" % self.module.id)
        line = self._cart_line()
        self.assertTrue(line)
        self.assertAlmostEqual(line.price_subtotal, 70.0)
        self.assertAlmostEqual(line.order_id.amount_total, 70.0)

    @freeze_time(AFTER_END, tick=True)
    def test_after_end_date_back_to_list_price(self):
        """Après le 31/12, rien à défaire : la règle expire, le prix catalogue revient."""
        self._launch_pricelist()
        self.authenticate(None, None)
        body = self.url_open(self.module.website_url).text
        self.assertNotIn("oski-price-offer", body)
        self.assertNotIn("Launch price", body)
        self.url_open("/apps/buy/%s" % self.module.id)
        line = self._cart_line()
        self.assertAlmostEqual(line.price_subtotal, 100.0)
