"""Le CTA « Demander un module » vit dans la navigation, la fin de grille et
l'état vide — jamais dans le hero (spec §3, maquette validée)."""
from lxml import html

from odoo.tests import tagged
from odoo.tests.common import HttpCase

FORM = "/apps/demande-developpement"


@tagged("post_install", "-at_install")
class TestCtaPlacement(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _doc(self, url="/apps"):
        return html.fromstring(self.url_open(url).text)

    def test_hero_has_no_request_link(self):
        doc = self._doc()
        hero_links = doc.xpath("//header[contains(@class,'oski-hero')]//a[@href='%s']" % FORM)
        self.assertEqual(hero_links, [])

    def test_navigation_menu_exists(self):
        menu = self.env.ref("oski_dev_request.menu_request_module")
        self.assertEqual(menu.url, FORM)
        doc = self._doc()
        nav_links = doc.xpath("//*[@id='top_menu']//a[@href='%s']" % FORM)
        self.assertTrue(nav_links, "lien de navigation absent")
