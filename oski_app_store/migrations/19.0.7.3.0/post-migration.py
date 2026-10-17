"""19.0.7.3.0 — Odoo 20 devient la version par défaut du catalogue.

Ses archives arrivent module par module (is_upcoming reste vrai, le bandeau
« archives en cours » l'explique) ; le visiteur ouvre le store sur la version
qu'il installe aujourd'hui. Référentiel en noupdate → le drapeau se déplace ici.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    v20 = env.ref("oski_app_store.odoo_version_20", raise_if_not_found=False)
    if not v20 or v20.on_request:
        return
    env["oski.odoo.version"].search([("is_default", "=", True)]).write({"is_default": False})
    v20.is_default = True
