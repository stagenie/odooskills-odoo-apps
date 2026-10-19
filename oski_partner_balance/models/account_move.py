from odoo import _, fields, models
from odoo.exceptions import AccessError


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
        # The view shows the flag to accounting managers only, but the field
        # (and its writable mirror `is_excluded` on the statement lines) was
        # open to any invoicing user over RPC: anyone allowed to read the
        # balance could silently take a document out of it.
        if ('oski_exclude_from_balance' in vals and not self.env.su
                and not self.env.user.has_group('account.group_account_manager')):
            raise AccessError(_(
                "Only accounting managers can exclude a document from the "
                "partner balance."))
        return super().write(vals)
