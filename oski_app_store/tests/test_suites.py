"""Suites (19.0.7.8.0) : bandeau du catalogue, filtre « Suites », encart des fiches.

Une suite est un module `oski_<famille>_suite` : reconnue à son nom, sans réglage,
pour que chaque nouvelle série apparaisse d'elle-même dans le bandeau.
"""
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase

from odoo.addons.oski_app_store.tests.common_i18n import activate_french


def _module(env, tech, price=0.0, deps=(), currency=None, categ=None, published=True):
    vals = {"name": tech.replace("_", " ").title(), "technical_name": tech,
            "is_free": not price, "price": price, "is_published": published,
            "summary": "Summary of %s" % tech,
            "dependency_ids": [Command.set([d.id for d in deps])]}
    if price:
        product = env["product.template"].create({
            "name": tech, "type": "service", "list_price": price,
            "taxes_id": [Command.set([])], "is_published": True, "sale_ok": True,
        })
        vals.update(product_tmpl_id=product.id, currency_id=currency.id if currency else False)
    return env["oski.module"].create(vals)


@tagged("post_install", "-at_install")
class TestSuiteModel(TransactionCase):

    def test_suite_recognised_by_its_name(self):
        suite = _module(self.env, "oski_zz_suite")
        app = _module(self.env, "oski_zz_app")
        self.assertTrue(suite.is_suite)
        self.assertFalse(app.is_suite)
        # Modifiable au backend malgré le calcul.
        app.is_suite = True
        self.assertTrue(app.is_suite)

    def test_members_cascade_without_sub_suites(self):
        base = _module(self.env, "oski_zz_base", 10)
        a = _module(self.env, "oski_zz_a", 20, deps=[base])
        b = _module(self.env, "oski_zz_b", 30)
        small = _module(self.env, "oski_zz_small_suite", 40, deps=[a])
        big = _module(self.env, "oski_zz_big_suite", 50, deps=[small, b])
        self.assertEqual(small._suite_members(), a | base)
        # La sous-suite est traversée, pas comptée.
        self.assertEqual(big._suite_members(), a | base | b)
        self.assertEqual(base._published_suites_including(), small | big)
        self.assertFalse(small._published_suites_including())


@tagged("post_install", "-at_install")
class TestSuitePages(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        cls.env["product.pricelist"].search([]).action_archive()
        currency = cls.env["website"].get_current_website().company_id.currency_id
        cls.app_a = _module(cls.env, "oski_qq_alpha", 60, currency=currency)
        cls.app_b = _module(cls.env, "oski_qq_beta", 40, currency=currency)
        cls.free = _module(cls.env, "oski_qq_core")
        # 100 à l'unité, 59 en suite : −41 %.
        cls.suite = _module(cls.env, "oski_qq_suite", 59, currency=currency,
                            deps=[cls.app_a, cls.app_b, cls.free])
        cls.suite.name = "Quokka Suite"
        # Suite sans économie : jamais présentée comme une affaire.
        cls.flat = _module(cls.env, "oski_qr_suite", 200, currency=currency, deps=[cls.app_b])
        cls.flat.name = "Flat Suite"

    def test_band_on_catalog_home(self):
        self.authenticate(None, None)
        body = self.url_open("/apps").text
        self.assertIn("oski-suites", body)
        self.assertIn("Complete suites", body)
        self.assertIn("Quokka Suite", body)
        self.assertIn("3 apps included", body)
        self.assertIn("Save 41%", body)
        self.assertIn("pricing=suite", body)
        # Badge « Suite » à la place de « Premium » sur la carte de la grille.
        self.assertIn("oski-badge-suite", body)
        flat_card = body[body.index("Flat Suite"):]
        flat_card = flat_card[:flat_card.index("</a>")]
        self.assertNotIn("Save", flat_card)
        self.assertNotIn("<del", flat_card)

    def test_band_hidden_when_filtering(self):
        self.authenticate(None, None)
        for url in ("/apps?pricing=free", "/apps?search=quokka"):
            self.assertNotIn('class="oski-suites"', self.url_open(url).text, url)

    def test_suites_filter(self):
        self.authenticate(None, None)
        body = self.url_open("/apps?pricing=suite").text
        self.assertIn("Quokka Suite", body)
        self.assertIn("Flat Suite", body)
        self.assertNotIn("Oski Qq Alpha", body)
        self.assertNotIn("Oski Qq Core", body)

    def test_callout_on_member_page(self):
        self.authenticate(None, None)
        body = self.url_open(self.app_a.website_url).text
        self.assertIn("oski-suite-callout", body)
        self.assertIn("Quokka Suite", body)
        self.assertIn(self.suite.website_url, body)
        self.assertIn("instead of", body)
        self.assertIn("See the suite", body)
        # Une app hors suite n'a pas d'encart.
        lone = _module(self.env, "oski_qq_lone", 10)
        self.assertNotIn("oski-suite-callout", self.url_open(lone.website_url).text)

    def test_own_saving_on_suite_page(self):
        self.authenticate(None, None)
        body = self.url_open(self.suite.website_url).text
        self.assertIn("oski-suite-own", body)
        self.assertIn("the suite saves you 41%", body)
        self.assertNotIn("oski-suite-callout", body)
        self.assertNotIn("oski-suite-own", self.url_open(self.flat.website_url).text)

    def test_french(self):
        activate_french(self.env)
        self.authenticate(None, None)
        body = self.url_open("/fr/apps").text
        self.assertIn("Suites complètes", body)
        self.assertIn("3 apps incluses", body)
        self.assertIn("−41 %", body)
        page = self.url_open("/fr" + self.app_a.website_url).text
        self.assertIn("Voir la suite", page)
        self.assertIn("au lieu de", page)
