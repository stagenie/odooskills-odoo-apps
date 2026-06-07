from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


def _make_module(env, technical_name, odoo_versions, is_free=True, published=True):
    """Crée un oski.module avec une oski.module.version (+ zip) par version Odoo.

    Returns: (module record, dict {odoo_version: version record}).
    """
    module = env["oski.module"].create(
        {
            "name": technical_name,
            "technical_name": technical_name,
            "is_free": is_free,
            "is_published": published,
        }
    )
    versions = {}
    for ov in odoo_versions:
        attachment = env["ir.attachment"].create(
            {
                "name": "%s-%s.zip" % (technical_name, ov),
                "raw": b"ZIPDATA",
                "mimetype": "application/zip",
            }
        )
        versions[ov] = env["oski.module.version"].create(
            {
                "module_id": module.id,
                "odoo_version": ov,
                "module_version": "%s.1.0.0" % ov,
                "attachment_id": attachment.id,
            }
        )
    return module, versions


@tagged("post_install", "-at_install")
class TestVersionHelpers(TransactionCase):
    def test_available_versions(self):
        module, _ = _make_module(self.env, "oski_av", ["19.0", "17.0"])
        self.assertEqual(module.available_versions(), {"19.0", "17.0"})

    def test_supports(self):
        module, _ = _make_module(self.env, "oski_sup", ["19.0"])
        self.assertTrue(module.supports("19.0"))
        self.assertFalse(module.supports("18.0"))

    def test_download_target_exact(self):
        module, versions = _make_module(self.env, "oski_dt", ["18.0", "19.0"])
        self.assertEqual(module.download_target("18.0"), versions["18.0"])

    def test_download_target_fallback(self):
        module, versions = _make_module(self.env, "oski_dtf", ["19.0"])
        # 17.0 non supporté → dernière dispo (19.0)
        self.assertEqual(module.download_target("17.0"), versions["19.0"])

    def test_download_target_empty(self):
        module = self.env["oski.module"].create(
            {"name": "oski_empty", "technical_name": "oski_empty"}
        )
        self.assertFalse(module.download_target("19.0"))


@tagged("post_install", "-at_install")
class TestCatalogVersionSelector(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_module_never_disappears(self):
        """Behavior B : un module 19.0-only reste affiché à ?v=18.0."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_only19", ["19.0"])
        # garde-fou : présent à v=19.0 (évite faux positif sur 404)
        resp = self.url_open("/apps?v=19.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_only19", resp.text)
        # toujours présent à v=18.0
        resp = self.url_open("/apps?v=18.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_only19", resp.text)

    def test_pill_active_marked(self):
        """La pastille de la version sélectionnée porte is-active."""
        self.authenticate(None, None)
        resp = self.url_open("/apps?v=17.0")
        self.assertIn("oski-pill is-active", resp.text)

    def test_card_pastilles_on_off(self):
        """Carte : dot 'on' pour version présente, 'off' pour absente."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_dots", ["19.0"])
        resp = self.url_open("/apps?v=19.0")
        self.assertIn("oski-dot on", resp.text)
        self.assertIn("oski-dot off", resp.text)

    def test_card_greyed_when_incompatible(self):
        """Carte d'un module 19.0-only grisée à ?v=18.0."""
        self.authenticate(None, None)
        _make_module(self.env, "oski_grey", ["19.0"])
        resp = self.url_open("/apps?v=18.0")
        self.assertIn("is-incompatible", resp.text)


@tagged("post_install", "-at_install")
class TestModulePageCTA(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_cta_fallback_label(self):
        """Module 19.0-only à ?v=17.0 → bouton 'Télécharger (19.0)'."""
        self.authenticate(None, None)
        module, versions = _make_module(self.env, "oski_cta_fb", ["19.0"])
        resp = self.url_open("%s?v=17.0" % module.website_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Télécharger (19.0)", resp.text)
        self.assertIn("/apps/download/%s" % versions["19.0"].id, resp.text)

    def test_cta_exact_label(self):
        """Module 18.0+19.0 à ?v=18.0 → bouton 'Télécharger (18.0)'."""
        self.authenticate(None, None)
        module, versions = _make_module(self.env, "oski_cta_ex", ["18.0", "19.0"])
        resp = self.url_open("%s?v=18.0" % module.website_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Télécharger (18.0)", resp.text)
        self.assertIn("/apps/download/%s" % versions["18.0"].id, resp.text)
