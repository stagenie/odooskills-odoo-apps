"""Ordre d'affichage des versions Odoo (plus récente d'abord) et pages légales."""
import pathlib
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

    def test_legal_notice_public(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/mentions-legales")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("AI Skills LLC", resp.text)
        self.assertIn("LWS", resp.text)

    def test_privacy_policy_public(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/confidentialite")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Politique de confidentialité", resp.text)
        self.assertIn("apps@odooskills.com", resp.text)

    def test_faq_public(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/faq")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Questions fréquentes", resp.text)
        self.assertIn("/my/apps", resp.text)
        self.assertIn("/apps/demande-developpement", resp.text)

    def test_faq_needs_no_javascript(self):
        """L'accordéon repose sur <details> : rien à charger, rien à casser."""
        self.authenticate(None, None)
        html = self.url_open("/apps/faq").text
        self.assertIn("<details", html)
        self.assertIn("<summary>", html)

    def test_footer_links_to_every_legal_page(self):
        """Les liens légaux suivent le visiteur sur toutes les pages."""
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        self.assertIn("oski-footer-legal", html)
        for url in ("/apps/conditions-utilisation", "/apps/mentions-legales",
                    "/apps/confidentialite", "/apps/faq"):
            self.assertIn(url, html, "lien %s absent du pied de page" % url)

    def test_no_stale_support_address(self):
        """Une seule boîte est communiquée : apps@odooskills.com."""
        self.authenticate(None, None)
        for url in ("/apps/faq", "/apps/confidentialite", "/apps/mentions-legales",
                    "/apps/conditions-utilisation"):
            self.assertNotIn("support@odooskills.com", self.url_open(url).text)


@tagged("post_install", "-at_install")
class TestSeoAndErrorPages(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_catalog_has_title_and_description(self):
        self.authenticate(None, None)
        html = self.url_open("/apps").text
        self.assertIn("<title>Modules Odoo |", html)
        self.assertTrue(
            re.search(r'<meta name="description" content="Modules Odoo pr[^"]+"', html),
            "le catalogue doit porter sa propre méta-description",
        )

    def test_module_page_title_is_the_module(self):
        """Chaque fiche porte son nom et son résumé, pas ceux du site."""
        self.authenticate(None, None)
        module, _ = _make_module(self.env, "oski_seo", ["19.0"])
        module.summary = "Un résumé qui doit finir en méta-description."
        html = self.url_open(module.website_url).text
        self.assertIn("<title>oski_seo |", html)
        self.assertIn('content="Un résumé qui doit finir en méta-description."', html)

    def test_module_page_share_image_is_the_icon(self):
        """Sans image propre, cent quarante-sept aperçus identiques."""
        self.authenticate(None, None)
        module, _ = _make_module(self.env, "oski_og", ["19.0"])
        # PNG 1×1 transparent
        module.image_1920 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        html = self.url_open(module.website_url).text
        self.assertIn("/web/image/oski.module/%s/image_1920" % module.id, html)

    def test_unpublished_module_is_not_indexed(self):
        """Une fiche non publiée ne doit pas entrer dans le sitemap."""
        module, _ = _make_module(self.env, "oski_hidden", ["19.0"], published=False)
        public = self.env.ref("base.public_user")
        visible = self.env["oski.module"].with_user(public).search([
            ("id", "=", module.id)
        ])
        self.assertFalse(visible, "le public ne doit pas voir la fiche non publiée")

    def test_support_page_public(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/support")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("apps@odooskills.com", resp.text)
        self.assertIn("Ce qui n'est pas couvert", resp.text)

    def test_support_page_promises_no_delay(self):
        """Le délai n'est pas tranché : la page ne doit rien promettre."""
        self.authenticate(None, None)
        html = self.url_open("/apps/support").text
        for promesse in ("48 h", "24 h", "48h", "24h", "heures ouvrées"):
            self.assertNotIn(promesse, html)

    def test_404_search_field_is_visible(self):
        """Le champ hérite du style du hero sombre : il doit être ré-habillé."""
        scss = pathlib.Path(__file__).parent.parent.joinpath(
            "static/src/scss/oski_app_store.scss").read_text()
        block = scss[scss.index(".oski-404-search"):]
        block = block[:block.index(".oski-404-foot")]
        self.assertIn("background: #fff", block)
        self.assertIn("border: 1px solid $oski-line", block)

    def test_404_is_branded_and_french(self):
        self.authenticate(None, None)
        resp = self.url_open("/apps/cette-page-nexiste-pas")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Cette page n'existe pas.", resp.text)
        self.assertIn("/apps", resp.text)
        self.assertNotIn("We couldn't find the page", resp.text)
