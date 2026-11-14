from odoo import fields, models


class ResCompany(models.Model):
    """Le réglage vit sur la société, pas dans un paramètre système.

    Une maison mère qui vend sur trois mois et une filiale qui vend à la
    semaine n'ont pas le même délai ; un paramètre global les forcerait au
    même chiffre.
    """

    _inherit = "res.company"

    oski_quote_expire_active = fields.Boolean(
        string="Expire Overdue Quotations", default=False,
        help="The scheduled action cancels every night the quotations whose "
             "expiration date has passed.")
    oski_quote_reminder_days = fields.Integer(
        string="Reminder Before Expiry (days)", default=3,
        help="Number of days before the expiration date when the "
             "salesperson gets a reminder activity. Zero: no reminder.")
