from odoo import fields, models


class ResCompany(models.Model):
    """Le réglage vit sur la société, pas dans un paramètre système.

    Une maison mère qui vend sur trois mois et une filiale qui vend à la
    semaine n'ont pas le même délai ; un paramètre global les forcerait au
    même chiffre.
    """

    _inherit = "res.company"

    oski_quote_expire_active = fields.Boolean(
        string="Périmer les devis échus", default=False,
        help="La tâche planifiée annule chaque nuit les devis dont la date de "
             "validité est dépassée.")
    oski_quote_reminder_days = fields.Integer(
        string="Relance avant échéance (jours)", default=3,
        help="Nombre de jours avant l'échéance où le vendeur reçoit une "
             "activité de relance. Zéro : aucune relance.")
