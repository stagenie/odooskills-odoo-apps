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

    def test_legal_pages_both_languages(self):
        for path, en_marker, fr_marker in (
            ("/apps/conditions-utilisation", "Terms of use", "Conditions d'utilisation"),
            ("/apps/faq", "Frequently asked questions", "Questions fréquentes"),
            ("/apps/support", "Support", "Support"),
        ):
            self.assertIn(en_marker, self.url_open(path).text, path)
            self.assertIn(fr_marker, self.url_open("/fr" + path).text, path)
