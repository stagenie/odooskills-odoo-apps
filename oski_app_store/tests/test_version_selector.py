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
