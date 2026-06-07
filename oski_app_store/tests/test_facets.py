from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


def _make_module(env, technical_name, odoo_versions=("19.0",), is_free=True,
                 published=True, category=None, tags=None):
    """Crée un oski.module (+ versions/zip) avec catégorie et tags optionnels."""
    vals = {
        "name": technical_name,
        "technical_name": technical_name,
        "is_free": is_free,
        "is_published": published,
    }
    if category:
        vals["category_id"] = category.id
    if tags:
        vals["tag_ids"] = [(6, 0, [t.id for t in tags])]
    module = env["oski.module"].create(vals)
    for ov in odoo_versions:
        attachment = env["ir.attachment"].create(
            {"name": "%s-%s.zip" % (technical_name, ov), "raw": b"ZIPDATA",
             "mimetype": "application/zip"}
        )
        env["oski.module.version"].create(
            {"module_id": module.id, "odoo_version": ov,
             "module_version": "%s.1.0.0" % ov, "attachment_id": attachment.id}
        )
    return module


@tagged("post_install", "-at_install")
class TestTagModel(TransactionCase):
    def test_tag_m2m_symmetric(self):
        tag_a = self.env["oski.module.tag"].create({"name": "Compta"})
        tag_b = self.env["oski.module.tag"].create({"name": "Web"})
        module = _make_module(self.env, "oski_tagged", tags=[tag_a, tag_b])
        self.assertEqual(module.tag_ids, tag_a | tag_b)
        self.assertIn(module, tag_a.module_ids)
