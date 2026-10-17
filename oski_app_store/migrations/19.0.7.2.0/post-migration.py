"""19.0.7.2.0 — la version 17.0 passe « à la demande ».

Odoo 20 est sorti : les versions suivies d'office sont 20, 19 et 18 (fenêtre de
support Odoo). Même mécanique que 19.0.7.1.0 : le référentiel est en noupdate,
le drapeau se pose par xmlid sur la base installée.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    record = env.ref("oski_app_store.odoo_version_17", raise_if_not_found=False)
    if record and not record.is_upcoming:
        record.on_request = True
