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

    def _module(self, name):
        return self.env["oski.module"].create({
            "name": name, "technical_name": name, "is_free": True, "is_published": True})

    def test_grid_ends_with_request_card(self):
        self._module("oski_cta_grid")
        doc = self._doc()
        cards = doc.xpath("//div[contains(@class,'oski-catalog')]//div[contains(@class,'row')]/div[@class='col']")
        self.assertTrue(cards)
        last = cards[-1]
        self.assertTrue(last.xpath(".//*[contains(@class,'oski-card-request')]"))
        self.assertTrue(last.xpath(".//a[@href='%s']" % FORM))

    def test_empty_state_offers_prefilled_request(self):
        cat = self.env["oski.module.category"].create({"name": "Construction"})
        doc = self._doc("/apps?search=site+planning&category=%d" % cat.id)
        self.assertFalse(doc.xpath("//*[contains(@class,'oski-card-request')]"))
        links = doc.xpath("//*[contains(@class,'oski-empty-actions')]//a[starts-with(@href,'%s?')]" % FORM)
        self.assertEqual(len(links), 1)
        self.assertIn("subject=site+planning", links[0].get("href"))
        self.assertIn("category=%d" % cat.id, links[0].get("href"))

    def test_form_prefilled_from_query(self):
        cat = self.env["oski.module.category"].create({"name": "Construction"})
        doc = self._doc("%s?subject=%s&category=%d" % (FORM, "x" * 200, cat.id))
        subject = doc.xpath("//input[@name='subject']")[0].get("value")
        self.assertEqual(len(subject), 120)
        selected = doc.xpath("//select[@name='category_id']/option[@selected]")
        self.assertEqual(selected[0].get("value"), str(cat.id))
