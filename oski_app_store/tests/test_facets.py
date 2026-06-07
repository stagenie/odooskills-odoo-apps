from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


def _make_module(env, technical_name, odoo_versions=("19.0",), is_free=True,
                 published=True, category=None, tags=None):
    """Crée un oski.module (+ versions/zip) avec catégorie et tags optionnels."""
    vals = {
        "name": technical_name,
        "technical_name": technical_name,
        "is_free": is_free,
        "is_published": published,
    }
    if category:
        vals["category_id"] = category.id
    if tags:
        vals["tag_ids"] = [(6, 0, [t.id for t in tags])]
    module = env["oski.module"].create(vals)
    for ov in odoo_versions:
        attachment = env["ir.attachment"].create(
            {"name": "%s-%s.zip" % (technical_name, ov), "raw": b"ZIPDATA",
             "mimetype": "application/zip"}
        )
        env["oski.module.version"].create(
            {"module_id": module.id, "odoo_version": ov,
             "module_version": "%s.1.0.0" % ov, "attachment_id": attachment.id}
        )
    return module


@tagged("post_install", "-at_install")
class TestTagModel(TransactionCase):
    def test_tag_m2m_symmetric(self):
        tag_a = self.env["oski.module.tag"].create({"name": "Compta"})
        tag_b = self.env["oski.module.tag"].create({"name": "Web"})
        module = _make_module(self.env, "oski_tagged", tags=[tag_a, tag_b])
        self.assertEqual(module.tag_ids, tag_a | tag_b)
        self.assertIn(module, tag_a.module_ids)


@tagged("post_install", "-at_install")
class TestFacets(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_filter_single_tag(self):
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tlinch"})
        _make_module(self.env, "oski_has_tag", tags=[tag])
        _make_module(self.env, "oski_no_tag")
        resp = self.url_open("/apps")
        self.assertIn("oski_has_tag", resp.text)
        self.assertIn("oski_no_tag", resp.text)
        resp = self.url_open("/apps?tag=%s" % tag.id)
        self.assertIn("oski_has_tag", resp.text)
        self.assertNotIn("oski_no_tag", resp.text)

    def test_filter_or_two_tags(self):
        self.authenticate(None, None)
        ta = self.env["oski.module.tag"].create({"name": "Tora"})
        tb = self.env["oski.module.tag"].create({"name": "Torb"})
        _make_module(self.env, "oski_ta", tags=[ta])
        _make_module(self.env, "oski_tb", tags=[tb])
        resp = self.url_open("/apps?tag=%s&tag=%s" % (ta.id, tb.id))
        self.assertIn("oski_ta", resp.text)
        self.assertIn("oski_tb", resp.text)

    def test_filter_pricing_free(self):
        self.authenticate(None, None)
        _make_module(self.env, "oski_gratos", is_free=True)
        _make_module(self.env, "oski_payant", is_free=False)
        resp = self.url_open("/apps")
        self.assertIn("oski_payant", resp.text)
        resp = self.url_open("/apps?pricing=free")
        self.assertIn("oski_gratos", resp.text)
        self.assertNotIn("oski_payant", resp.text)

    def test_filter_pricing_premium(self):
        self.authenticate(None, None)
        _make_module(self.env, "oski_gr2", is_free=True)
        _make_module(self.env, "oski_pay2", is_free=False)
        resp = self.url_open("/apps?pricing=premium")
        self.assertIn("oski_pay2", resp.text)
        self.assertNotIn("oski_gr2", resp.text)

    def test_filter_multi_category_or(self):
        self.authenticate(None, None)
        c1 = self.env["oski.module.category"].create({"name": "Cat1"})
        c2 = self.env["oski.module.category"].create({"name": "Cat2"})
        _make_module(self.env, "oski_c1", category=c1)
        _make_module(self.env, "oski_c2", category=c2)
        resp = self.url_open("/apps?category=%s&category=%s" % (c1.id, c2.id))
        self.assertIn("oski_c1", resp.text)
        self.assertIn("oski_c2", resp.text)

    def test_and_across_groups(self):
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tand"})
        c1 = self.env["oski.module.category"].create({"name": "CatA"})
        c2 = self.env["oski.module.category"].create({"name": "CatB"})
        _make_module(self.env, "oski_tag_c1", category=c1, tags=[tag])
        resp = self.url_open("/apps?tag=%s&category=%s" % (tag.id, c2.id))
        self.assertNotIn("oski_tag_c1", resp.text)

    def test_sort_recent(self):
        self.authenticate(None, None)
        old = _make_module(self.env, "oski_old")
        new = _make_module(self.env, "oski_new")
        self.env.cr.execute(
            "UPDATE oski_module SET create_date = '2020-01-01 00:00:00' WHERE id = %s",
            (old.id,),
        )
        self.env.cr.execute(
            "UPDATE oski_module SET create_date = '2024-01-01 00:00:00' WHERE id = %s",
            (new.id,),
        )
        self.env.invalidate_all()
        resp = self.url_open("/apps?sort=recent")
        # le plus récent (oski_new) apparaît avant oski_old
        self.assertLess(resp.text.index("oski_new"), resp.text.index("oski_old"))

    def test_chip_present_and_linked(self):
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tchip"})
        _make_module(self.env, "oski_chipmod", tags=[tag])
        resp = self.url_open("/apps")
        self.assertIn("oski-chip", resp.text)
        self.assertIn('href="/apps?tag=%s"' % tag.id, resp.text)

    def test_active_filters_bar(self):
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tactive"})
        _make_module(self.env, "oski_af", tags=[tag])
        resp = self.url_open("/apps?tag=%s" % tag.id)
        self.assertIn("oski-active-filters", resp.text)

    def test_facet_panel_rendered(self):
        self.authenticate(None, None)
        self.env["oski.module.tag"].create({"name": "Tpanel"})
        resp = self.url_open("/apps")
        self.assertIn("oski-facets", resp.text)
