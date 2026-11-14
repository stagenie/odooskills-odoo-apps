"""Essais enregistrés avec un code de langue court (« en ») → code Odoo actif."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Trial = env["oski.module.trial"].with_context(active_test=False)
    for trial in Trial.search([("lang", "!=", False)]):
        code = Trial._normalize_lang(trial.lang)
        if code != trial.lang:
            trial.lang = code
