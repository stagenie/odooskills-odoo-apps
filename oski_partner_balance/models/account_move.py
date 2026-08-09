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

    def write(self, vals):
        result = super().write(vals)
        if 'oski_exclude_from_balance' in vals:
            # oski.partner.balance.line#is_excluded is a related field on a
            # TransientModel. The ORM does not register a recompute trigger
            # from a regular model onto a transient one (see
            # Field.resolve_depends), so an already-cached wizard line would
            # keep showing the old value. Invalidate it explicitly.
            self.env['oski.partner.balance.line'].search(
                [('move_id', 'in', self.ids)]).invalidate_recordset(['is_excluded'])
        return result
