from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    oski_operation_datetime = fields.Datetime(
        string='Operation Date & Time',
        default=fields.Datetime.now,
        index=True,
        copy=False,
        help="Used to order same-day operations on the partner statement. "
             "Defaults to the creation time and can be corrected.",
    )
    oski_exclude_from_balance = fields.Boolean(
        string='Exclude from Partner Balance',
        default=False,
        copy=False,
        help="When ticked, this document is left out of the partner balance, "
             "of the statement and of the opening balance.",
    )
