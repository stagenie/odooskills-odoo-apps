"""19.0.7.7.4 — statistiques du store.

1. Premier calcul des compteurs `stat_*` (sinon à 0 jusqu'au premier cron horaire).
2. Point de départ des compteurs PUBLICS (décision du 16/11) : l'historique d'avant
   comptait les contrôles automatiques (publish_check) ; il reste dans le journal et
   dans l'Analyse, mais la fiche publique ne compte qu'à partir de cette mise à jour.
3. Compteurs publics affichés, seuil 10 (paramètres posés seulement s'ils sont absents).
"""
from odoo import SUPERUSER_ID, api, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Param = env["ir.config_parameter"].sudo()
    if not Param.get_param("oski_app_store.public_counter_since"):
        Param.set_param(
            "oski_app_store.public_counter_since", fields.Datetime.to_string(fields.Datetime.now())
        )
    if not Param.get_param("oski_app_store.show_counters"):
        Param.set_param("oski_app_store.show_counters", "True")
    if not Param.get_param("oski_app_store.counters_min"):
        Param.set_param("oski_app_store.counters_min", "10")
    env["oski.module"]._stats_refresh()
