from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase

from odoo.addons.oski_app_store.tests.common_i18n import activate_french


def _ver(env, name):
    rec = env["oski.odoo.version"].search([("name", "=", name)], limit=1)
    if not rec:
        raise ValueError("oski.odoo.version %r absente du référentiel" % name)
    return rec


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
            {"module_id": module.id, "odoo_version_id": _ver(env, ov).id,
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

    def test_no_tag_row_in_catalog(self):
        """19.0.7.7.6 : plus de rangée d'étiquettes, même si des étiquettes existent."""
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tlinch"})
        _make_module(self.env, "oski_has_tag", tags=[tag])
        _make_module(self.env, "oski_no_tag")
        resp = self.url_open("/apps")
        self.assertIn("oski_has_tag", resp.text)
        self.assertIn("oski_no_tag", resp.text)
        self.assertNotIn("oski-tag-chips", resp.text)
        self.assertNotIn("Tlinch", resp.text)
        self.assertNotIn("?tag=", resp.text)

    def test_old_tag_link_redirects_without_tag(self):
        """Un ancien lien `?tag=` ne casse rien : 301 vers la même vue sans étiquette."""
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tora"})
        _make_module(self.env, "oski_ta", tags=[tag])
        _make_module(self.env, "oski_tb")
        for raw in (str(tag.id), "1", "abc"):
            resp = self.url_open("/apps?tag=%s&pricing=free" % raw, allow_redirects=False)
            self.assertEqual(resp.status_code, 301, raw)
            location = resp.headers["Location"]
            self.assertNotIn("tag=", location)
            self.assertTrue(location.endswith("/apps?pricing=free"), location)
        resp = self.url_open("/apps?tag=%s" % tag.id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_ta", resp.text)
        self.assertIn("oski_tb", resp.text)

    def test_pricing_labels_open_source(self):
        """Sélecteur Prix : All prices / Open source / Premium ; badge Open source."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_os_badge", is_free=True)
        html = self.url_open("/apps").text
        for label in ("All prices", "Open source", "Premium"):
            self.assertIn(label, html)
        self.assertIn('oski-badge-free">Open source<', html)
        self.assertNotRegex(html, r">\s*Free\s*<")

    def test_pricing_labels_open_source_french(self):
        activate_french(self.env)
        self.authenticate(None, None)
        _make_module(self.env, "oski_os_badge_fr", is_free=True)
        html = self.url_open("/fr/apps").text
        for label in ("Tous les prix", "Open source", "Premium"):
            self.assertIn(label, html)
        self.assertIn('oski-badge-free">Open source<', html)
        self.assertNotIn("Gratuit", html)
        self.assertNotIn("gratuits", html)

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
        c1 = self.env["oski.module.category"].create({"name": "CatA"})
        c2 = self.env["oski.module.category"].create({"name": "CatB"})
        _make_module(self.env, "oski_free_c1", category=c1, is_free=True)
        _make_module(self.env, "oski_paid_c1", category=c1, is_free=False)
        _make_module(self.env, "oski_free_c2", category=c2, is_free=True)
        resp = self.url_open("/apps?pricing=free&category=%s" % c1.id)
        self.assertIn("oski_free_c1", resp.text)
        self.assertNotIn("oski_paid_c1", resp.text)
        self.assertNotIn("oski_free_c2", resp.text)

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

    def test_active_filters_bar(self):
        """Quand des filtres sont actifs, le lien 'Tout effacer' est affiché."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_af")
        resp = self.url_open("/apps?pricing=free")
        self.assertIn("oski-clear", resp.text)

    def test_facet_panel_rendered(self):
        """La barre de filtres (toolbar) est présente dans le catalogue."""
        self.authenticate(None, None)
        self.env["oski.module.tag"].create({"name": "Tpanel"})
        resp = self.url_open("/apps")
        self.assertIn("oski-toolbar", resp.text)

    def test_empty_state_without_dev_request_keeps_reset(self):
        body = self.url_open("/apps?search=nothing-matches-this").text
        self.assertIn("oski-empty-state", body)
        self.assertIn("No module for", body)
        self.assertIn('href="/apps"', body)


@tagged("post_install", "-at_install")
class TestModulePageChips(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_page_shows_no_tag_chips(self):
        """19.0.7.7.6 : la fiche n'affiche plus d'étiquettes ; badge Open source."""
        self.authenticate(None, None)
        tag = self.env["oski.module.tag"].create({"name": "Tpage"})
        module = _make_module(self.env, "oski_pagetag", tags=[tag])
        resp = self.url_open(module.website_url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Tpage", resp.text)
        self.assertNotIn("/apps?tag=", resp.text)
        self.assertIn('oski-badge-free">Open source<', resp.text)
