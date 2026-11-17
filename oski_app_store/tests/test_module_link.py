from odoo.tests import HttpCase, tagged

from .common_i18n import activate_french


@tagged("post_install", "-at_install")
class TestModuleLink(HttpCase):
    """`/apps/m/<technical_name>` : lien stable écrit dans les fiches (suites)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _module(self, technical_name, published=True, description=False):
        return self.env["oski.module"].create({
            "name": "Link Test %s" % technical_name,
            "technical_name": technical_name,
            "summary": "Résumé",
            "is_published": published,
            "description_html": description,
        })

    def test_redirects_to_canonical_page(self):
        module = self._module("oski_link_test_ok")
        self.authenticate(None, None)
        resp = self.url_open("/apps/m/oski_link_test_ok", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.headers["Location"].endswith(module.website_url))
        page = self.url_open("/apps/m/oski_link_test_ok")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Link Test oski_link_test_ok", page.text)

    def test_french_link_stays_french(self):
        activate_french(self.env)
        module = self._module("oski_link_test_fr")
        self.authenticate(None, None)
        resp = self.url_open("/fr/apps/m/oski_link_test_fr", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertIn("/fr" + module.website_url, resp.headers["Location"])

    def test_unknown_or_unpublished_is_404(self):
        self._module("oski_link_test_hidden", published=False)
        self.authenticate(None, None)
        self.assertEqual(self.url_open("/apps/m/oski_link_test_hidden").status_code, 404)
        self.assertEqual(self.url_open("/apps/m/oski_does_not_exist").status_code, 404)

    def test_lightbox_rendered_without_screenshots(self):
        """La description peut contenir des images même sans galerie : le
        modal d'agrandissement doit être là pour elles."""
        module = self._module(
            "oski_link_test_zoom",
            description='<p><img src="/web/image/1" alt="x"/></p>',
        )
        self.assertFalse(module.screenshot_ids)
        self.authenticate(None, None)
        html = self.url_open(module.website_url).text
        self.assertIn('id="oskiLightbox"', html)
        self.assertIn("oski-desc", html)


@tagged("post_install", "-at_install")
class TestScreenshotsByLang(HttpCase):
    """Galerie EN sur la page anglaise, galerie FR sur la page française."""

    def _shot(self, name):
        return self.env["ir.attachment"].create({
            "name": name, "raw": b"png", "public": True, "mimetype": "image/png",
        })

    def test_gallery_follows_language(self):
        en1 = self._shot("oski_lang_shot/screenshot_01_list.png")
        fr1 = self._shot("oski_lang_shot/screenshot_01_list_fr.png")
        module = self.env["oski.module"].create({
            "name": "Lang Shot", "technical_name": "oski_lang_shot",
            "is_published": True, "screenshot_ids": [(6, 0, [en1.id, fr1.id])],
        })
        self.assertEqual(module._screenshots_for_lang("en_US"), en1)
        self.assertEqual(module._screenshots_for_lang("fr_FR"), fr1)

    def test_french_page_falls_back_to_english_series(self):
        en1 = self._shot("oski_lang_only_en/screenshot_01_list.png")
        module = self.env["oski.module"].create({
            "name": "Lang Only EN", "technical_name": "oski_lang_only_en",
            "is_published": True, "screenshot_ids": [(6, 0, [en1.id])],
        })
        self.assertEqual(module._screenshots_for_lang("fr_FR"), en1)
