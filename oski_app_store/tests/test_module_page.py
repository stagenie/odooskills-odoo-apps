import base64

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestModulePage(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _make_module_with_shot(self, technical_name):
        """Crée un module publié avec une capture d'écran et une version zip."""
        v19 = self.env["oski.odoo.version"].search([("name", "=", "19.0")])
        att_zip = self.env["ir.attachment"].create(
            {"name": "m.zip", "datas": base64.b64encode(b"zip"), "public": True}
        )
        shot = self.env["ir.attachment"].create(
            {
                "name": "screenshot_01.png",
                "datas": base64.b64encode(b"png"),
                "public": True,
            }
        )
        module = self.env["oski.module"].create(
            {
                "name": "Module Page Test",
                "technical_name": technical_name,
                "summary": "Résumé test",
                "description_html": "<h2>Doc détaillée</h2>",
                "is_published": True,
                "screenshot_ids": [(6, 0, [shot.id])],
                "version_line_ids": [
                    (0, 0, {
                        "odoo_version_id": v19.id,
                        "module_version": "19.0.1.0.0",
                        "attachment_id": att_zip.id,
                    })
                ],
            }
        )
        return module

    def test_page_structure(self):
        module = self._make_module_with_shot("oski_page_test_struct")
        self.authenticate(None, None)
        resp = self.url_open(module.website_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("oski-techcard", html)       # carte technique
        self.assertIn("oski-gallery", html)        # carrousel
        self.assertIn("oski-desc", html)           # description pleine largeur
        self.assertIn("Doc détaillée", html)
        self.assertIn("/apps/download/", html)     # bouton télécharger

    def test_page_no_screenshots_full_width(self):
        v19 = self.env["oski.odoo.version"].search([("name", "=", "19.0")])
        att_zip = self.env["ir.attachment"].create(
            {"name": "m2.zip", "datas": base64.b64encode(b"zip2"), "public": True}
        )
        module_no_shots = self.env["oski.module"].create(
            {
                "name": "Module No Shots",
                "technical_name": "oski_page_test_noshots",
                "summary": "Sans captures",
                "is_published": True,
                "version_line_ids": [
                    (0, 0, {
                        "odoo_version_id": v19.id,
                        "module_version": "19.0.1.0.0",
                        "attachment_id": att_zip.id,
                    })
                ],
            }
        )
        self.authenticate(None, None)
        resp = self.url_open(module_no_shots.website_url)
        self.assertEqual(resp.status_code, 200)  # garde anti faux-positif 404
        html = resp.text
        self.assertNotIn("oski-gallery", html)
        self.assertIn("oski-techcard-wide", html)  # carte pleine largeur

    def test_gallery_sorted_by_name(self):
        """Les captures doivent apparaître triées par nom de fichier (01 avant 02)."""
        v19 = self.env["oski.odoo.version"].search([("name", "=", "19.0")])
        # Créer screenshot_01 EN PREMIER → id inférieur
        # Sans .sorted("name"), id desc placerait screenshot_02 (id supérieur) avant screenshot_01
        shot1 = self.env["ir.attachment"].create(
            {"name": "screenshot_01.png", "datas": base64.b64encode(b"a"), "public": True}
        )
        shot2 = self.env["ir.attachment"].create(
            {"name": "screenshot_02.png", "datas": base64.b64encode(b"b"), "public": True}
        )
        module = self.env["oski.module"].create(
            {
                "name": "Gallery Order",
                "technical_name": "oski_gallery_order",
                "is_published": True,
                "screenshot_ids": [(6, 0, [shot2.id, shot1.id])],
            }
        )
        self.authenticate(None, None)
        resp = self.url_open(module.website_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertLess(
            html.find("screenshot_01.png"), html.find("screenshot_02.png"),
            "Galerie triée par nom de fichier",
        )
