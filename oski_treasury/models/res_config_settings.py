# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # NOTE: transfer control (insufficient balance blocking / manager
    # force) is implemented per-record in oski.treasury.transfer
    # (`force_transfer` field) and oski.treasury.cash (`control_level`,
    # `allow_negative_balance`), not via global toggles. The source
    # treasor_pack had three extra transfer_* config_parameter fields here
    # that were never read by any model — dropped to avoid dead settings.

    # --- Cash operation accounting entries ---
    treasury_account_move_enabled = fields.Boolean(
        string='Generate Accounting Entries',
        config_parameter='oski_treasury.account_move_enabled',
        default=True,
        help="Creates an accounting entry (account.move) when a cash "
             "operation is posted. Operations originating from a payment "
             "(account.payment) are linked to their native entry without "
             "duplication.",
    )
    treasury_cash_account_id = fields.Many2one(
        'account.account', string='Default Cash Account',
        config_parameter='oski_treasury.default_cash_account_id',
        domain="[('active', '=', True)]",
    )
    treasury_revenue_account_id = fields.Many2one(
        'account.account', string='Default Revenue Account',
        config_parameter='oski_treasury.default_revenue_account_id',
        domain="[('active', '=', True)]",
    )
    treasury_expense_account_id = fields.Many2one(
        'account.account', string='Default Expense Account',
        config_parameter='oski_treasury.default_expense_account_id',
        domain="[('active', '=', True)]",
    )
    treasury_transfer_account_id = fields.Many2one(
        'account.account', string='Internal Transfer Account',
        config_parameter='oski_treasury.default_transfer_account_id',
        domain="[('active', '=', True)]",
        help="Transit account used as the counterpart for transfer "
             "operations (cash register <-> safe <-> bank).",
    )
    treasury_journal_id = fields.Many2one(
        'account.journal', string='Treasury Entries Journal',
        config_parameter='oski_treasury.journal_id',
        domain="[('type', 'in', ('cash', 'general'))]",
        help="Journal used for the accounting entries of cash operations. "
             "If empty, the cash register's journal is used.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        Account = self.env['account.account']
        company = self.env.company

        param_field = {
            'oski_treasury.default_cash_account_id': 'treasury_cash_account_id',
            'oski_treasury.default_revenue_account_id': 'treasury_revenue_account_id',
            'oski_treasury.default_expense_account_id': 'treasury_expense_account_id',
        }

        def _auto(param_key, account_types):
            """Auto-detects a chart of accounts account if not yet configured."""
            if params.get_param(param_key):
                return
            account = Account.search([
                ('account_type', 'in', account_types),
                ('active', '=', True),
                ('company_ids', 'in', company.id),
            ], limit=1)
            if account:
                res[param_field[param_key]] = account.id

        _auto('oski_treasury.default_cash_account_id', ['asset_cash'])
        _auto('oski_treasury.default_revenue_account_id',
              ['income', 'income_other'])
        _auto('oski_treasury.default_expense_account_id',
              ['expense', 'expense_direct_cost'])
        return res
