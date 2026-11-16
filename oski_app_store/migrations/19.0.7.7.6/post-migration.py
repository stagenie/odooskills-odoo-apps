"""19.0.7.7.6 — plus d'étiquettes dans le catalogue public.

Les 10 étiquettes présentes en production sont des restes de démonstration
(attachées à 1 ou 2 modules chacune) : elles sont supprimées, par xml-id
(`tag_demo_*`, fichier retiré du manifeste) et par nom anglais. Une étiquette
créée plus tard sous un autre nom n'est pas touchée.
"""
from odoo import SUPERUSER_ID, api

DEMO_TAG_NAMES = (
    "Free", "Example", "PDF report", "Ergonomics", "Alert", "Cron",
    "Notification", "Productivity", "Tracking", "Invoicing",
)
DEMO_XMLIDS = ("tag_demo_gratuit", "tag_demo_exemple")


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Tag = env["oski.module.tag"].with_context(active_test=False)
    tags = Tag.browse()
    for xmlid in DEMO_XMLIDS:
        tags |= env.ref("oski_app_store.%s" % xmlid, raise_if_not_found=False) or Tag
    tags |= Tag.with_context(lang="en_US").search([("name", "in", DEMO_TAG_NAMES)])
    if tags:
        tags.unlink()
    env["ir.model.data"].search([
        ("module", "=", "oski_app_store"), ("name", "in", DEMO_XMLIDS),
    ]).unlink()
