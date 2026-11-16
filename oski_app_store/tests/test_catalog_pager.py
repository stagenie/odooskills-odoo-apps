"""Pagination du catalogue /apps : 24 cartes par page, filtres conservés."""
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.oski_app_store.controllers.main import CATALOG_PAGE_SIZE
from odoo.addons.oski_app_store.tests.common_i18n import activate_french
from odoo.addons.oski_app_store.tests.test_facets import _make_module

# Carte module de la grille (la carte « demande » d'oski_dev_request porte
# une classe de plus, elle n'est pas comptée).
CARD = 'class="oski-card h-100"'
TOTAL = 30


@tagged("post_install", "-at_install")
class TestCatalogPager(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        # Catalogue maîtrisé : seuls les modules du test sont publiés.
        cls.env["oski.module"].search([]).write({"is_published": False})
        cls.mods = [
            _make_module(cls.env, "oski_pg_%02d" % i)
            for i in range(1, TOTAL + 1)
        ]

    def _get(self, url, **kw):
        self.authenticate(None, None)
        return self.url_open(url, **kw)

    def test_page_size_fills_every_grid(self):
        # 1, 2, 3 et 4 colonnes : une page pleine n'a jamais de rangée trouée.
        for cols in (1, 2, 3, 4):
            self.assertEqual(CATALOG_PAGE_SIZE % cols, 0)

    def test_page_one_and_two(self):
        p1 = self._get("/apps")
        self.assertEqual(p1.status_code, 200)
        self.assertEqual(p1.text.count(CARD), CATALOG_PAGE_SIZE)
        self.assertIn("oski_pg_01", p1.text)
        self.assertIn("oski_pg_24", p1.text)
        self.assertNotIn("oski_pg_25", p1.text)
        self.assertIn('href="/apps/page/2"', p1.text)
        self.assertIn('<link rel="next" href="/apps/page/2"', p1.text)
        self.assertNotIn('rel="prev"', p1.text)

        p2 = self._get("/apps/page/2")
        self.assertEqual(p2.status_code, 200)
        self.assertEqual(p2.text.count(CARD), TOTAL - CATALOG_PAGE_SIZE)
        self.assertIn("oski_pg_25", p2.text)
        self.assertIn("oski_pg_30", p2.text)
        self.assertNotIn("oski_pg_24", p2.text)
        self.assertIn('<link rel="prev" href="/apps"', p2.text)
        self.assertNotIn('rel="next"', p2.text)

    def test_counter_is_the_total(self):
        for url in ("/apps", "/apps/page/2"):
            self.assertIn("%d modules" % TOTAL, self._get(url).text)

    def test_seo_canonical_and_title_of_page_two(self):
        html = self._get("/apps/page/2").text
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
        self.assertTrue(canonical.endswith("/apps/page/2"), canonical)
        t1 = re.search(r"<title>([^<]*)</title>", self._get("/apps").text).group(1)
        t2 = re.search(r"<title>([^<]*)</title>", html).group(1)
        self.assertNotEqual(t1, t2)
        self.assertIn("page 2 of 2", t2)

    def test_filters_kept_in_pager_links(self):
        url = "/apps?pricing=free&search=oski_pg&sort=recent"
        html = self._get(url).text
        links = re.findall(r'href="(/apps/page/2\?[^"]*)"', html)
        self.assertTrue(links, "lien vers la page 2 absent")
        for link in links:
            for part in ("pricing=free",
                         "search=oski_pg", "sort=recent"):
                self.assertIn(part, link.replace("&amp;", "&"))
        p2 = self._get(links[0].replace("&amp;", "&"))
        self.assertEqual(p2.text.count(CARD), TOTAL - CATALOG_PAGE_SIZE)

    def test_filter_link_returns_to_page_one(self):
        html = self._get("/apps/page/2").text
        self.assertIn('href="/apps?pricing=free"', html)

    def test_out_of_range_redirects_to_last_page(self):
        resp = self._get("/apps/page/9?pricing=free", allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        self.assertTrue(resp.headers["Location"].endswith(
            "/apps/page/2?pricing=free"), resp.headers["Location"])
        resp = self._get("/apps/page/1", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.headers["Location"].endswith("/apps"))
        resp = self._get("/apps/page/0", allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        self.assertTrue(resp.headers["Location"].endswith("/apps"))

    def test_small_catalog_has_no_pager(self):
        html = self._get("/apps?search=oski_pg_1").text  # 10 à 19
        self.assertNotIn('class="oski-pager"', html)
        self.assertNotIn("/apps/page/2", html)

    def test_request_card_only_on_last_page(self):
        if "oski.dev.request" not in self.env:
            self.skipTest("oski_dev_request non installé")
        self.assertNotIn("oski-card-request", self._get("/apps").text)
        self.assertIn("oski-card-request", self._get("/apps/page/2").text)

    def test_french_pager(self):
        activate_french(self.env)
        html = self._get("/fr/apps").text
        self.assertIn('href="/fr/apps/page/2"', html)
        self.assertIn("%d modules" % TOTAL, html)
        p2 = self._get("/fr/apps/page/2")
        self.assertEqual(p2.status_code, 200)
        self.assertEqual(p2.text.count(CARD), TOTAL - CATALOG_PAGE_SIZE)
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', p2.text).group(1)
        self.assertTrue(canonical.endswith("/fr/apps/page/2"), canonical)
        resp = self._get("/fr/apps/page/9", allow_redirects=False)
        self.assertTrue(resp.headers["Location"].endswith("/fr/apps/page/2"),
                        resp.headers["Location"])
        resp = self._get("/fr/apps/page/1", allow_redirects=False)
        self.assertTrue(resp.headers["Location"].endswith("/fr/apps"),
                        resp.headers["Location"])

    def test_pages_after_the_first_are_noindex(self):
        # Choix standard d'Odoo 19 (website.layout) : page > 1 = noindex,
        # les liens restent suivis ; les fiches modules sont dans le sitemap.
        self.assertNotIn('content="noindex"', self._get("/apps").text)
        self.assertIn('content="noindex"', self._get("/apps/page/2").text)

    def test_sitemap_still_lists_catalog(self):
        self.env["ir.attachment"].search([("url", "=like", "/sitemap%"),
                                          ("res_model", "=", False)]).unlink()
        xml = self._get("/sitemap.xml").text
        self.assertIn("/apps</loc>", xml)
        self.assertNotIn("/apps/page/", xml)

    def test_back_link_returns_to_the_same_page(self):
        module = self.mods[-1]
        referer = self.base_url() + "/apps/page/2?pricing=free"
        html = self._get(module.website_url, headers={"Referer": referer}).text
        self.assertIn('class="oski-back" href="/apps/page/2?pricing=free"', html)
        referer = self.base_url() + "/apps/page/2/../../../evil"
        html = self._get(module.website_url, headers={"Referer": referer}).text
        self.assertIn('class="oski-back" href="/apps"', html)
