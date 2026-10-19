"""19.0.7.1.0 — les versions 15.0 et 16.0 passent « à la demande ».

Le référentiel oski.odoo.version est chargé en noupdate="1" : une base déjà
installée ne relit pas le fichier de données, donc le nouveau drapeau
`on_request` y resterait faux. On le pose ici, par xmlid, et seulement sur
les fiches d'origine : une version ajoutée ou renommée à la main n'est pas
touchée.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in ("oski_app_store.odoo_version_15", "oski_app_store.odoo_version_16"):
        record = env.ref(xmlid, raise_if_not_found=False)
        if record and not record.is_upcoming:
            record.on_request = True
