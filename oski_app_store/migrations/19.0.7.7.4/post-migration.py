"""19.0.7.7.4 — statistiques du store : premier calcul des compteurs `stat_*`.

Sans cela, les colonnes triables restent à 0 jusqu'au premier passage du cron horaire.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["oski.module"]._stats_refresh()
