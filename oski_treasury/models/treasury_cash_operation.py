# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TreasuryCashOperation(models.Model):
    _name = 'oski.treasury.cash.operation'
    _description = 'Treasury Cash Operation'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    cash_id = fields.Many2one(
        'oski.treasury.cash', string='Cash Register', required=True,
        ondelete='restrict', tracking=True,
    )
    operation_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out'),
    ], string='Type', required=True, tracking=True)
    category_id = fields.Many2one(
        'oski.treasury.operation.category', string='Category', required=True,
    )
    amount = fields.Monetary(
        string='Amount', required=True, tracking=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', related='cash_id.currency_id', store=True,
    )
    date = fields.Datetime(
        string='Date', required=True, default=fields.Datetime.now,
        tracking=True,
    )
    description = fields.Text(string='Description')
    reference = fields.Char(string='External Reference')
    partner_id = fields.Many2one('res.partner', string='Partner')
    observations = fields.Text(string='Observations')

    # --- Links ---
    payment_id = fields.Many2one(
        'account.payment', string='Payment', readonly=True,
    )
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True, copy=False,
    )
    transfer_id = fields.Many2one(
        'oski.treasury.transfer', string='Transfer', readonly=True,
    )
    closing_id = fields.Many2one(
        'oski.treasury.cash.closing', string='Closing', readonly=True,
    )
    is_manual = fields.Boolean(string='Manual Operation', default=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments',
    )

    # --- State ---
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    user_id = fields.Many2one(
        'res.users', string='Created By', readonly=True,
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company', related='cash_id.company_id', store=True,
    )

    # --- Time-based computed fields ---
    is_today = fields.Boolean(compute='_compute_date_filters')
    is_this_week = fields.Boolean(compute='_compute_date_filters')
    is_this_month = fields.Boolean(compute='_compute_date_filters')

    def _compute_date_filters(self):
        now = fields.Datetime.now()
        for op in self:
            if op.date:
                op.is_today = op.date.date() == now.date()
                # ISO week
                op.is_this_week = op.date.isocalendar()[1] == now.isocalendar()[1] and op.date.year == now.year
                op.is_this_month = op.date.month == now.month and op.date.year == now.year
            else:
                op.is_today = op.is_this_week = op.is_this_month = False

    # --- Constraints ---

    @api.constrains('amount')
    def _check_amount(self):
        for op in self:
            if op.amount <= 0:
                raise ValidationError(_("The amount must be strictly positive."))

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.treasury.cash.operation'
                ) or _('New')
        return super().create(vals_list)

    def unlink(self):
        for op in self:
            if op.state == 'posted':
                raise UserError(
                    _("Cannot delete a posted operation. Cancel it first.")
                )
            if op.closing_id and op.closing_id.state == 'validated':
                raise UserError(
                    _("Cannot delete an operation linked to a validated closing.")
                )
            if op.transfer_id:
                raise UserError(
                    _("Cannot delete an operation linked to a transfer. "
                      "Cancel the transfer first.")
                )
        return super().unlink()

    # --- Workflow actions ---

    def action_post(self):
        for op in self:
            if op.state != 'draft':
                raise UserError(_("Only draft operations can be posted."))
            # Balance check for outgoing operations (neutralized by a forced
            # transfer: the control was already assumed at transfer level)
            if (op.operation_type == 'out'
                    and not self.env.context.get('oski_treasury_force_transfer')
                    and not op.cash_id.allow_negative_balance):
                if op.cash_id.current_balance < op.amount:
                    if op.cash_id.control_level == 'blocking':
                        raise UserError(
                            _("Insufficient balance in cash register '%s'. "
                              "Balance: %s, Amount: %s",
                              op.cash_id.name,
                              op.cash_id.current_balance,
                              op.amount)
                        )
            op.state = 'posted'
            # Auto-link to the ongoing closing if not already linked
            if not op.closing_id:
                pending_closing = self.env['oski.treasury.cash.closing'].search([
                    ('cash_id', '=', op.cash_id.id),
                    ('state', 'in', ('draft', 'confirmed')),
                ], order='closing_date desc, closing_number desc', limit=1)
                if pending_closing:
                    op.closing_id = pending_closing
            # Accounting entry (configurable, non-blocking)
            op._create_account_move()

    # --- Accounting ---

    def _treasury_account_move_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'oski_treasury.account_move_enabled', 'True'
        ) in ('True', 'true', '1', True)

    def _get_move_accounts(self):
        """Returns (debit_account, credit_account) for the operation, or
        (False, False).

        Priority: explicit accounts of the category, otherwise the default
        accounts from Treasury Settings (cash + revenue/expense/transfer)."""
        self.ensure_one()
        Account = self.env['account.account']
        category = self.category_id
        # Explicit accounts of the category: only for a category dedicated to
        # a precise direction (in OR out). A 'both' category cannot carry a
        # correct debit/credit pair for both directions -> fall back to the
        # default accounts (which apply the direction based on operation_type).
        if (category.debit_account_id and category.credit_account_id
                and category.operation_type == self.operation_type):
            return category.debit_account_id, category.credit_account_id

        params = self.env['ir.config_parameter'].sudo()

        def _acc(key):
            val = params.get_param(key)
            if not val:
                return Account
            acc = Account.browse(int(val))
            return acc if acc.exists() else Account

        cash_account = _acc('oski_treasury.default_cash_account_id')
        if self.transfer_id:
            counterpart = _acc('oski_treasury.default_transfer_account_id')
        elif self.operation_type == 'in':
            counterpart = _acc('oski_treasury.default_revenue_account_id')
        else:
            counterpart = _acc('oski_treasury.default_expense_account_id')

        if not (cash_account and counterpart):
            return Account, Account

        if self.operation_type == 'in':
            return cash_account, counterpart  # debit cash / credit counterpart
        return counterpart, cash_account  # debit counterpart / credit cash

    def _get_treasury_journal(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        journal_id = params.get_param('oski_treasury.journal_id')
        if journal_id:
            return self.env['account.journal'].browse(int(journal_id))
        return self.cash_id.journal_id

    def _create_account_move(self):
        """Creates the operation's accounting entry if the feature is enabled.

        Anti-duplication guard: an operation originating from a payment
        (account.payment) is linked to the payment's native entry, without
        recreating one. Non-blocking: if the configuration is incomplete,
        the operation stays posted on the treasury side with a message on
        the chatter."""
        self.ensure_one()
        if self.move_id or not self._treasury_account_move_enabled():
            return
        # Internal treasury movement (cash/safe/bank transfer): no GL entry
        # here. Both legs would use the same accounts (net zero, loss of
        # per-cash-register traceability) and the safe/bank leg does not
        # generate a move (transit account never settled).
        if self.transfer_id:
            return
        # Link to the payment's native entry (no duplication)
        if self.payment_id and self.payment_id.move_id:
            self.move_id = self.payment_id.move_id
            return

        debit_account, credit_account = self._get_move_accounts()
        if not (debit_account and credit_account):
            self.message_post(body=_(
                "Accounting entry not created: accounts not configured. "
                "Set up the accounts in Settings > Treasury or on the category."
            ))
            return
        journal = self._get_treasury_journal()
        if not journal:
            self.message_post(body=_(
                "Accounting entry not created: no treasury journal."
            ))
            return

        label = self.description or self.category_id.name or self.name
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date.date() if self.date else fields.Date.today(),
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'account_id': debit_account.id,
                    'partner_id': self.partner_id.id or False,
                    'name': label,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': credit_account.id,
                    'partner_id': self.partner_id.id or False,
                    'name': label,
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ],
        })
        move.action_post()
        self.move_id = move

    def _remove_own_account_move(self):
        """Removes the operation's own entry (not a payment's)."""
        self.ensure_one()
        move = self.move_id
        if not move or self.payment_id:
            return
        self.move_id = False
        if move.state == 'posted':
            move.button_draft()
        move.unlink()

    def action_cancel(self):
        for op in self:
            if op.closing_id and op.closing_id.state == 'validated':
                raise UserError(
                    _("Cannot cancel an operation in a validated closing.")
                )
            op._remove_own_account_move()
            op.state = 'cancel'

    def action_draft(self):
        for op in self:
            if op.state != 'cancel':
                raise UserError(_("Only cancelled operations can be reset to draft."))
            op.state = 'draft'

    def action_reset_to_draft(self):
        """Resets a posted operation to draft (formerly oski_treasury_access)"""
        for op in self:
            if op.state != 'posted':
                raise UserError(_("Only posted operations can be reset."))
            if op.closing_id and op.closing_id.state == 'validated':
                raise UserError(
                    _("Cannot reset: operation in a validated closing.")
                )
            op._remove_own_account_move()
            op.state = 'draft'
