import base64

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestDownloadController(HttpCase):
    """Teste le contrôleur /apps/download/<version_id>.

    Cas couverts :
    - module gratuit publié → 200 + contenu zip
    - module payant, visiteur public → redirect (302/303)
    - module non publié → 404
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Le cache de routage peut avoir été construit avant le chargement du
        # contrôleur oski_app_store (les modules installés avant, comme website,
        # peuvent le peupler). On force la régénération pour inclure nos routes.
        cls.env.registry.clear_cache('routing')
        cls.addClassCleanup(cls.env.registry.clear_cache, 'routing')

    def _make_module(self, technical_name, is_free=True, published=True):
        """Crée une fixture (oski.module + version + pièce jointe zip).

        Returns:
            tuple: (oski.module record, oski.module.version record)
        """
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.zip" % technical_name,
                "raw": b"ZIPDATA",
                "mimetype": "application/zip",
            }
        )
        module = self.env["oski.module"].create(
            {
                "name": technical_name,
                "technical_name": technical_name,
                "is_free": is_free,
                "is_published": published,
            }
        )
        version = self.env["oski.module.version"].create(
            {
                "module_id": module.id,
                "odoo_version": "19.0",
                "module_version": "19.0.1.0.0",
                "attachment_id": attachment.id,
            }
        )
        return module, version

    def test_free_download_public_ok(self):
        """Un visiteur public peut télécharger un module gratuit publié."""
        self.authenticate(None, None)
        _, version = self._make_module("oski_free", is_free=True)
        resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"ZIPDATA")

    def test_paid_download_public_redirects(self):
        """Un visiteur public accédant à un module payant est redirigé."""
        self.authenticate(None, None)
        module, version = self._make_module("oski_paid", is_free=False)
        resp = self.url_open(
            "/apps/download/%s" % version.id, allow_redirects=False
        )
        self.assertIn(resp.status_code, (302, 303))

    def test_unpublished_download_not_found(self):
        """Un module non publié retourne 404 quel que soit le visiteur."""
        self.authenticate(None, None)
        _, version = self._make_module("oski_hidden", is_free=True, published=False)
        resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.status_code, 404)

    def test_catalog_lists_published(self):
        """Le catalogue /apps affiche les modules publiés."""
        self.authenticate(None, None)
        self._make_module("oski_catalog_pub", is_free=True, published=True)
        resp = self.url_open("/apps")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_catalog_pub", resp.text)

    def test_catalog_hides_unpublished(self):
        """Le catalogue /apps masque les modules non publiés."""
        self.authenticate(None, None)
        self._make_module("oski_catalog_hidden", is_free=True, published=True)
        resp = self.url_open("/apps")
        self.assertIn("oski_catalog_hidden", resp.text)
        # Une fois dépublié, le module disparaît du catalogue.
        hidden = self.env["oski.module"].search(
            [("technical_name", "=", "oski_catalog_hidden")]
        )
        hidden.is_published = False
        resp = self.url_open("/apps")
        self.assertNotIn("oski_catalog_hidden", resp.text)

    def test_module_page_published_ok(self):
        """La page /apps/<slug> d'un module publié répond 200."""
        self.authenticate(None, None)
        module, _ = self._make_module("oski_page_pub", is_free=True, published=True)
        resp = self.url_open(module.website_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_page_pub", resp.text)

    def test_module_page_unpublished_404(self):
        """La page d'un module non publié est invisible au public (404)."""
        self.authenticate(None, None)
        module, _ = self._make_module(
            "oski_page_hidden", is_free=True, published=False
        )
        resp = self.url_open("/apps/oski_page_hidden-%s" % module.id)
        self.assertEqual(resp.status_code, 404)
