"""Compteurs : comptés dès le premier jour, affichés plus tard (spec §2)."""
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestCounters(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        cls.v19 = cls.env["oski.odoo.version"].search([("name", "=", "19.0")], limit=1)

    def _module(self, name, is_free=True, price=0.0):
        product = self.env["product.template"]
        if not is_free:
            product = product.create({"name": name, "type": "service", "list_price": price,
                                      "taxes_id": [(6, 0, [])], "is_published": True})
        module = self.env["oski.module"].create({
            "name": name, "technical_name": name, "is_free": is_free, "is_published": True,
            "price": price, "product_tmpl_id": product.id if product else False,
        })
        att = self.env["ir.attachment"].create({"name": name + ".zip", "raw": b"ZIP",
                                                "mimetype": "application/zip"})
        version = self.env["oski.module.version"].create({
            "module_id": module.id, "odoo_version_id": self.v19.id,
            "module_version": "19.0.1.0.0", "attachment_id": att.id})
        return module, version

    def test_free_download_increments(self):
        """Une même session ne compte qu'une fois par version (garde 6 h) ;
        une autre session (autres cookies) compte à part."""
        module, version = self._module("oski_cnt_free")
        self.assertEqual(version.download_count, 0)
        self.assertEqual(self.url_open("/apps/download/%d" % version.id).status_code, 200)
        self.url_open("/apps/download/%d" % version.id)
        version.invalidate_recordset(["download_count"])
        self.assertEqual(version.download_count, 1)

        self.opener.cookies.clear()
        self.assertEqual(self.url_open("/apps/download/%d" % version.id).status_code, 200)
        version.invalidate_recordset(["download_count"])
        self.assertEqual(version.download_count, 2)
        self.assertEqual(module.download_count, 2)

    def test_refused_download_does_not_count(self):
        module, version = self._module("oski_cnt_paid", is_free=False, price=19.0)
        r = self.url_open("/apps/download/%d" % version.id, allow_redirects=False)
        self.assertEqual(r.status_code, 303)
        version.invalidate_recordset(["download_count"])
        self.assertEqual(version.download_count, 0)

    def test_purchase_count_distinct_partners(self):
        module, _ = self._module("oski_cnt_buy", is_free=False, price=19.0)
        variant = module.product_tmpl_id.product_variant_id
        p1 = self.env["res.partner"].create({"name": "Buyer one"})
        p2 = self.env["res.partner"].create({"name": "Buyer two"})
        for partner in (p1, p1, p2):
            order = self.env["sale.order"].create({
                "partner_id": partner.id,
                "order_line": [(0, 0, {"product_id": variant.id, "product_uom_qty": 1})],
            })
            order.action_confirm()
        draft = self.env["sale.order"].create({
            "partner_id": p2.id,
            "order_line": [(0, 0, {"product_id": variant.id, "product_uom_qty": 1})],
        })
        self.assertEqual(draft.state, "draft")
        self.assertEqual(module.purchase_count, 2)

    def test_purchase_count_batched_across_modules(self):
        """Deux fiches calculées dans le même recordset : un seul _read_group,
        chacune avec le bon nombre d'acheteurs distincts."""
        module_a, _va = self._module("oski_cnt_batch_a", is_free=False, price=19.0)
        module_b, _vb = self._module("oski_cnt_batch_b", is_free=False, price=29.0)
        variant_a = module_a.product_tmpl_id.product_variant_id
        variant_b = module_b.product_tmpl_id.product_variant_id
        pa1 = self.env["res.partner"].create({"name": "Batch buyer A1"})
        pa2 = self.env["res.partner"].create({"name": "Batch buyer A2"})
        pb1 = self.env["res.partner"].create({"name": "Batch buyer B1"})
        for partner, variant in ((pa1, variant_a), (pa2, variant_a), (pb1, variant_b)):
            order = self.env["sale.order"].create({
                "partner_id": partner.id,
                "order_line": [(0, 0, {"product_id": variant.id, "product_uom_qty": 1})],
            })
            order.action_confirm()

        both = module_a + module_b
        both.invalidate_recordset(["purchase_count"])
        self.assertEqual(module_a.purchase_count, 2)
        self.assertEqual(module_b.purchase_count, 1)

    def _set(self, show, minimum=10):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param("oski_app_store.show_counters", "True" if show else "False")
        Param.set_param("oski_app_store.counters_min", str(minimum))

    def test_counters_hidden_by_default(self):
        module, version = self._module("oski_cnt_hidden")
        version.write({"download_count": 500})
        self.assertNotIn("oski-count", self.url_open("/apps").text)
        self.assertNotIn("oski-count", self.url_open(module.website_url).text)

    def test_counters_shown_above_threshold_only(self):
        module, version = self._module("oski_cnt_shown")
        version.write({"download_count": 12})
        self._set(True, minimum=10)
        page = self.url_open(module.website_url).text
        self.assertIn('class="oski-count"', page)
        catalog = self.url_open("/apps").text
        self.assertRegex(
            catalog,
            re.compile(r'class="oski-count"[^>]*>.*?</svg>\s*12\s*</span>', re.S),
        )
        version.write({"download_count": 3})
        self.assertNotIn("oski-count", self.url_open(module.website_url).text)

    def test_sort_by_downloads_only_when_visible(self):
        self._set(False)
        self.assertNotIn("sort=downloads", self.url_open("/apps").text)
        self._set(True)
        self.assertIn("sort=downloads", self.url_open("/apps").text)
