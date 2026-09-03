from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_lost_reason_required = fields.Boolean(
        string="Motif de perte obligatoire", default=True,
        help="Interdit de perdre une opportunité sans dire pourquoi.")
    oski_lost_feedback_required = fields.Boolean(
        string="Note de clôture obligatoire", default=False,
        help="Exige en plus quelques mots de contexte, au-delà du motif choisi "
             "dans la liste.")
