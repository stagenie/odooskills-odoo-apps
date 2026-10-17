"""19.0.7.4.0 — Odoo 20 est une version suivie comme les autres.

Plus de bandeau « archives en cours » : la 20.0 est sortie, elle est le défaut
du catalogue, et chaque fiche dit d'elle-même quelles archives existent.
Référentiel en noupdate → le drapeau se retire ici.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    v20 = env.ref("oski_app_store.odoo_version_20", raise_if_not_found=False)
    if v20 and v20.is_upcoming:
        v20.is_upcoming = False
