"""Ordre d'affichage des versions Odoo (plus récente d'abord) et pages légales."""
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.oski_app_store.tests.test_version_selector import _make_module

EXPECTED_ORDER = ["20.0", "19.0", "18.0", "17.0", "16.0", "15.0"]


@tagged("post_install", "-at_install")
class TestVersionOrder(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_filter_dropdown_starts_with_20(self):
        """Sélecteur Version : 20.0 en tête, 15.0 en queue."""
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        listed = re.findall(r"dropdown-item[^>]*>\s*([0-9]{2}\.0)", html)
        self.assertEqual(listed, EXPECTED_ORDER)

    def test_spectrum_starts_with_20(self):
        """Frise du hero : même ordre, 20 d'abord."""
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        listed = re.findall(r"oski-spectrum-node[^>]*>\s*<span>([0-9]{2})</span>", html)
        self.assertEqual(listed, [v.split(".")[0] for v in EXPECTED_ORDER])

    def test_upcoming_marked_soon(self):
        """La 20.0 se distingue : classe is-soon + mention dans le sélecteur."""
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        self.assertIn("is-soon", html)
        self.assertIn("oski-opt-note", html)
        self.assertIn("est à la porte", html)

    def test_card_dots_skip_upcoming(self):
        """Aucune pastille 20 sur les cartes : rien à télécharger en 20.0."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_dots20", ["19.0"])
        html = self.url_open("/apps").text
        self.assertTrue(re.search(r'oski-dot[^>]*>19<', html), "pastille 19 attendue")
        self.assertIsNone(
            re.search(r'oski-dot[^>]*>20<', html),
            "une pastille toujours éteinte n'apprend rien au visiteur",
        )

    def test_upcoming_selected_shows_notice(self):
        """?v=20.0 : le catalogue le dit au lieu de laisser croire à un bug."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_notice20", ["19.0"])
        resp = self.url_open("/apps?v=20.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski-notice", resp.text)
        self.assertIn("n'est pas encore sortie", resp.text)
        self.assertIn("oski_notice20", resp.text, "Behavior B : rien n'est masqué")

    def test_module_page_pill_20_soon(self):
        """Fiche : pastille 20.0 présente, marquée à venir et sans archive."""
        self.authenticate(None, None)
        module, _ = _make_module(self.env, "oski_pill20", ["19.0"])
        html = self.url_open(module.website_url).text
        self.assertTrue(
            re.search(r'oski-vpill[^"]*soon[^"]*"[^>]*>20\.0', html),
            "la 20.0 doit apparaître marquée 'soon' sur la fiche",
        )

    def test_module_page_20_falls_back_to_19(self):
        """?v=20.0 sur une fiche : téléchargement de la dernière version réelle."""
        self.authenticate(None, None)
        module, versions = _make_module(self.env, "oski_fb20", ["19.0"])
        html = self.url_open("%s?v=20.0" % module.website_url).text
        self.assertIn("Télécharger (19.0)", html)
        self.assertIn("Indisponible en 20.0", html)


@tagged("post_install", "-at_install")
class TestLegalPages(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_terms_page_public(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/conditions-utilisation")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Conditions d'utilisation", resp.text)
        self.assertIn("apps@odooskills.com", resp.text)

    def test_terms_page_published(self):
        page = self.env.ref("oski_app_store.terms_of_use_page")
        self.assertTrue(page.is_published)
        self.assertEqual(page.url, "/apps/conditions-utilisation")

    def test_footer_links_to_terms(self):
        """Le lien légal suit le visiteur sur toutes les pages."""
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        self.assertIn("oski-footer-legal", html)
        self.assertIn("/apps/conditions-utilisation", html)
