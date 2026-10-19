"""Bandeaux promotionnels sur les fiches (carte du catalogue et page module).

Le bandeau est un `product.ribbon` (website_sale) posé sur le module, borné par
deux dates facultatives : hors fenêtre, rien ne s'affiche.
"""
import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestRibbon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        cls.ribbon = cls.env["product.ribbon"].create(
            {
                "name": "Black Friday",
                "bg_color": "#111111",
                "text_color": "#FFD400",
                "style": "tag",
                "position": "right",
            }
        )
        v19 = cls.env["oski.odoo.version"].search([("name", "=", "19.0")])
        att = cls.env["ir.attachment"].create(
            {"name": "r.zip", "datas": base64.b64encode(b"zip"), "public": True}
        )
        cls.module = cls.env["oski.module"].create(
            {
                "name": "Promo Band Test Module",
                "technical_name": "oski_promo_band_test",
                "summary": "Ribbon summary",
                "is_published": True,
                "version_line_ids": [
                    (0, 0, {
                        "odoo_version_id": v19.id,
                        "module_version": "19.0.1.0.0",
                        "attachment_id": att.id,
                    })
                ],
            }
        )

    def test_no_ribbon_by_default(self):
        self.assertFalse(self.module.ribbon_display_id)

    def test_ribbon_without_dates_is_displayed(self):
        self.module.ribbon_id = self.ribbon
        self.assertEqual(self.module.ribbon_display_id, self.ribbon)

    def test_ribbon_hidden_outside_window(self):
        today = fields.Date.today()
        self.module.write({
            "ribbon_id": self.ribbon.id,
            "ribbon_date_from": today - timedelta(days=10),
            "ribbon_date_to": today - timedelta(days=1),
        })
        self.assertFalse(self.module.ribbon_display_id, "expired ribbon must not show")
        self.module.write({
            "ribbon_date_from": today + timedelta(days=1),
            "ribbon_date_to": today + timedelta(days=10),
        })
        self.assertFalse(self.module.ribbon_display_id, "future ribbon must not show")
        self.module.write({
            "ribbon_date_from": today,
            "ribbon_date_to": today,
        })
        self.assertEqual(self.module.ribbon_display_id, self.ribbon, "bounds are inclusive")

    def test_dates_must_be_ordered(self):
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.module.write({
                "ribbon_id": self.ribbon.id,
                "ribbon_date_from": today,
                "ribbon_date_to": today - timedelta(days=1),
            })

    def test_catalog_card_and_page_show_ribbon_to_public(self):
        self.module.ribbon_id = self.ribbon
        self.authenticate(None, None)
        card = self.url_open("/apps?q=oski_promo_band_test").text
        self.assertIn("oski-ribbon", card)
        self.assertIn("Black Friday", card)
        self.assertIn("oski-ribbon-tag", card)
        self.assertIn("oski-ribbon-right", card)
        self.assertIn("background:#111111", card.replace(" ", ""))
        page = self.url_open(self.module.website_url).text
        self.assertIn("oski-ribbon", page)
        self.assertIn("Black Friday", page)

    def test_catalog_hides_expired_ribbon(self):
        today = fields.Date.today()
        self.module.write({
            "ribbon_id": self.ribbon.id,
            "ribbon_date_to": today - timedelta(days=1),
        })
        self.authenticate(None, None)
        card = self.url_open("/apps?q=oski_promo_band_test").text
        self.assertIn("Promo Band Test Module", card)
        self.assertNotIn("oski-ribbon", card)
        self.assertNotIn("Black Friday", card)

    def test_manager_can_manage_ribbons(self):
        manager = self.env["res.users"].create({
            "name": "Store Manager", "login": "oski_ribbon_manager",
            "group_ids": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("oski_app_store.group_manager").id,
            ])],
        })
        Ribbon = self.env["product.ribbon"].with_user(manager)
        rec = Ribbon.create({"name": "On sale", "bg_color": "#000000", "text_color": "#FFFFFF"})
        rec.name = "Special offer"
        rec.unlink()
