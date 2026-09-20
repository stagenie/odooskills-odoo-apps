"""Versions servies à la demande, et formulation ouverte de la compatibilité.

Le catalogue n'annonce plus de borne haute (« jusqu'à la 19.0 ») : elle vieillit
à chaque sortie d'Odoo. Il dit depuis quelle version les modules sont suivis,
et quelles versions plus anciennes restent possibles sur demande.
"""
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


@tagged("post_install", "-at_install")
class TestVersionOnRequestRegistry(TransactionCase):
    def test_15_and_16_are_on_request(self):
        Version = self.env["oski.odoo.version"]
        self.assertTrue(self.env.ref("oski_app_store.odoo_version_15").on_request)
        self.assertTrue(self.env.ref("oski_app_store.odoo_version_16").on_request)
        self.assertEqual(Version.get_on_request(), ["16.0", "15.0"])

    def test_standard_excludes_upcoming_and_on_request(self):
        self.assertEqual(
            self.env["oski.odoo.version"].get_standard(),
            ["19.0", "18.0", "17.0"],
        )

    def test_released_still_lists_on_request(self):
        """Une version à la demande est sortie : ses archives restent filtrables."""
        self.assertEqual(
            self.env["oski.odoo.version"].get_released(),
            ["19.0", "18.0", "17.0", "16.0", "15.0"],
        )

    def test_default_flag_on_an_on_request_version_is_ignored(self):
        """Un « défaut » coché par erreur sur la 16.0 n'ouvre pas le catalogue dessus."""
        Version = self.env["oski.odoo.version"]
        Version.search([]).write({"is_default": False})
        self.env.ref("oski_app_store.odoo_version_16").is_default = True
        self.assertEqual(Version.get_default(), "19.0")

    def test_default_falls_back_when_only_on_request_remain(self):
        """Mieux vaut ouvrir sur une version à la demande que sur un catalogue vide."""
        Version = self.env["oski.odoo.version"]
        Version.search([("name", "in", ("19.0", "18.0", "17.0"))]).unlink()
        self.assertEqual(Version.get_default(), "16.0")

    def test_upcoming_cannot_be_on_request(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env["oski.odoo.version"].create(
                {"name": "21.0", "sequence": 210, "is_upcoming": True, "on_request": True}
            )


@tagged("post_install", "-at_install")
class TestOpenCompatibilityWording(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _catalog(self):
        self.authenticate(None, None)
        return self.url_open("/apps").text

    def test_hero_has_no_upper_bound(self):
        html = self._catalog()
        self.assertIn("for Odoo 17 and later", html)
        self.assertNotIn("compatible from", html)

    def test_hero_names_on_request_versions(self):
        self.assertIn("Odoo 15, 16 on request", self._catalog())

    def test_selector_marks_on_request(self):
        html = self._catalog()
        self.assertIn("is-on-request", html)
        self.assertTrue(
            re.search(r'dropdown-item[^>]*>\s*16\.0\s*<[^>]*oski-opt-note[^>]*>\s*on request', html),
            "la 16.0 doit porter la mention « on request » dans le sélecteur",
        )

    def test_meta_description_is_open(self):
        html = self._catalog()
        meta = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
        self.assertIn("Odoo 17 and later", meta)
        self.assertNotIn("19.0", meta)

    def test_released_odoo_is_not_called_unreleased(self):
        """Odoo 20 est sorti : « à venir » veut dire archives en cours, pas version absente."""
        html = self._catalog()
        self.assertNotIn("at the door", html)
        self.assertNotIn("not released yet", html)
        self.assertIn("archives on the way", html)

    def test_faq_covers_on_request_and_20(self):
        self.authenticate(None, None)
        html = self.url_open("/apps/faq").text
        self.assertNotIn("at the door", html)
        self.assertIn("on request", html)
        self.assertIn("ported", html)


@tagged("post_install", "-at_install")
class TestFrenchTemplateIsCurrent(TransactionCase):
    """Le lecteur de .po d'Odoo filtre par le .pot voisin : une traduction dont
    la source manque au .pot est jetée sans un mot, et la page française sort
    en anglais. Tout msgid de fr.po doit donc exister dans le .pot."""

    def test_every_french_entry_is_in_the_template(self):
        import pathlib

        import polib

        i18n = pathlib.Path(__file__).resolve().parents[1] / "i18n"
        template = {e.msgid for e in polib.pofile(str(i18n / "oski_app_store.pot"))}
        orphans = [
            e.msgid for e in polib.pofile(str(i18n / "fr.po"))
            if e.msgid and e.msgid not in template
        ]
        self.assertFalse(orphans, "absents du .pot, donc ignorés par Odoo : %s" % orphans[:5])

    def test_on_request_is_read_in_french(self):
        import pathlib

        from odoo.tools.translate import PoFileReader

        po = pathlib.Path(__file__).resolve().parents[1] / "i18n" / "fr.po"
        with open(po, "rb") as handle:
            values = {row["src"]: row["value"] for row in PoFileReader(handle)}
        self.assertEqual(values.get("on request"), "à la demande")
