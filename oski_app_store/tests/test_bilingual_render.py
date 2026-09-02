"""Le store se lit en anglais par défaut et en français sous /fr."""
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .common_i18n import activate_french


@tagged("post_install", "-at_install")
class TestBilingualRender(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        activate_french(cls.env)

    def test_catalog_english_by_default(self):
        body = self.url_open("/apps").text
        self.assertIn("Give Odoo", body)
        self.assertIn('lang="en-US"', body)
        self.assertNotIn("Donnez à Odoo", body)

    def test_catalog_french_under_fr_prefix(self):
        body = self.url_open("/fr/apps").text
        self.assertIn("Donnez à Odoo", body)
        self.assertIn('lang="fr-FR"', body)
        # Odoo raccourcit le hreflang au code court (res_lang.py) : "en", pas "en-US".
        self.assertIn('hreflang="en"', body)   # lien alterné vers l'anglais

    def test_module_page_labels_both_languages(self):
        module = self.env["oski.module"].create({
            "name": "Bilingual demo", "technical_name": "oski_bilingual_demo",
            "is_free": True, "is_published": True,
        })
        en = self.url_open(module.website_url).text
        fr = self.url_open("/fr" + module.website_url).text
        self.assertIn("Technical name", en)
        self.assertIn("Nom technique", fr)
        self.assertIn("Back to catalog", en)
        self.assertIn("Retour au catalogue", fr)

    def test_module_url_has_no_canonical_redirect(self):
        """La page module ne redirige jamais vers l'URL basée sur le nom :
        le canonical du framework (ir.http._slug) doit lui aussi suivre le
        nom technique, sinon l'URL réellement affichée change avec la
        langue malgré website_url stable."""
        module = self.env["oski.module"].create({
            "name": "Alerte de stock bas",
            "technical_name": "oski_stock_low_alert_canon",
            "is_free": True, "is_published": True,
        })
        # Vérifié EN PREMIER, avant toute visite en /fr : sinon le cookie
        # frontend_lang posé par la requête /fr ci-dessous ferait passer
        # cette requête sans préfixe par la branche « lang manquante dans
        # l'URL » (redirection 303 non liée au canonical testé ici).
        # L'ancienne URL basée sur le nom traduit doit toujours fonctionner
        # (redirection permanente), mais pointer vers l'URL technique stable.
        old_name_url = "/apps/alerte-de-stock-bas-%d" % module.id
        redirect = self.url_open(old_name_url, allow_redirects=False)
        self.assertEqual(redirect.status_code, 301)
        self.assertTrue(redirect.headers["Location"].endswith(module.website_url))

        en = self.url_open(module.website_url, allow_redirects=False)
        self.assertEqual(en.status_code, 200)
        fr = self.url_open("/fr" + module.website_url, allow_redirects=False)
        self.assertEqual(fr.status_code, 200)

    def test_legal_pages_both_languages(self):
        for path, en_marker, fr_marker in (
            ("/apps/conditions-utilisation", "Terms of use", "Conditions d'utilisation"),
            ("/apps/faq", "Frequently asked questions", "Questions fréquentes"),
            ("/apps/support", "Support", "Support"),
        ):
            self.assertIn(en_marker, self.url_open(path).text, path)
            self.assertIn(fr_marker, self.url_open("/fr" + path).text, path)
