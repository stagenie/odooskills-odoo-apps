# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TreasurySafeOperation(models.Model):
    _name = 'oski.treasury.safe.operation'
    _description = 'Treasury Safe Operation'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    safe_id = fields.Many2one(
        'oski.treasury.safe', string='Safe', required=True,
        ondelete='restrict', tracking=True,
    )
    operation_type = fields.Selection([
        ('initial', 'Initialization'),
        ('bank_in', 'Bank In'),
        ('bank_out', 'Bank Out'),
        ('adjustment', 'Adjustment'),
        ('other_in', 'Other In'),
        ('other_out', 'Other Out'),
    ], string='Type', required=True, tracking=True)
    amount = fields.Monetary(
        string='Amount', required=True, currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', related='safe_id.currency_id', store=True,
    )
    date = fields.Datetime(
        string='Date', required=True, default=fields.Datetime.now,
    )
    bank_reference = fields.Char(string='Bank Reference')
    description = fields.Text(string='Description', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    user_id = fields.Many2one(
        'res.users', string='Created By', readonly=True,
        default=lambda self: self.env.user,
    )
    validated_by = fields.Many2one('res.users', string='Validated By', readonly=True)
    company_id = fields.Many2one(
        'res.company', related='safe_id.company_id', store=True,
    )
    transfer_id = fields.Many2one(
        'oski.treasury.transfer', string='Transfer', readonly=True,
    )

    # --- Compute ---

    balance_before = fields.Monetary(
        string='Balance Before', currency_field='currency_id',
        compute='_compute_balances',
    )
    balance_after = fields.Monetary(
        string='Balance After', currency_field='currency_id',
        compute='_compute_balances',
    )

    # D3 hardening: historical balance_before/balance_after. The source
    # (treasor_pack treasury_safe_operation.py:71, "Simplifie : utilise le
    # solde actuel du coffre") derived both balances from the safe's live
    # current_balance, which is wrong for anything but the very last
    # operation. Here each operation's balances reflect the state of the
    # safe strictly BEFORE it, ordered by (date, id) -- deterministic
    # tiebreaker on ties, same lesson as the v15 balance_fix incident.
    @api.depends('safe_id', 'amount', 'operation_type', 'state', 'date')
    def _compute_balances(self):
        for op in self:
            if not op.safe_id:
                op.balance_before = op.balance_after = 0.0
                continue
            domain = [
                ('safe_id', '=', op.safe_id.id),
                ('state', '=', 'done'),
                ('id', '!=', op.id),
            ]
            previous = self.search(domain).filtered(
                lambda o: (o.date, o.id) < (op.date, op.id or float('inf'))
            )
            balance = 0.0
            for prev in previous:
                balance += prev._signed_amount()
            op.balance_before = balance
            op.balance_after = balance + (
                op._signed_amount() if op.state == 'done' else 0.0
            )

    def _signed_amount(self):
        """Signed contribution of this operation to the safe's balance.

        Mirrors the grouping used by TreasurySafe._compute_current_balance:
        initial/bank_in/other_in/adjustment add to the balance, bank_out/
        other_out subtract. `amount` is always strictly positive (enforced
        by `_check_amount`), so this is the single source of truth for the
        sign convention -- used by both this compute and the safe's."""
        self.ensure_one()
        in_types = ('initial', 'bank_in', 'other_in', 'adjustment')
        return self.amount if self.operation_type in in_types else -self.amount

    # --- Constraints ---

    @api.constrains('amount')
    def _check_amount(self):
        for op in self:
            if op.amount <= 0:
                raise ValidationError(_("The amount must be strictly positive."))

    @api.constrains('operation_type', 'safe_id')
    def _check_single_init(self):
        for op in self:
            if op.operation_type == 'initial':
                existing = self.search_count([
                    ('safe_id', '=', op.safe_id.id),
                    ('operation_type', '=', 'initial'),
                    ('state', '!=', 'cancel'),
                    ('id', '!=', op.id),
                ])
                if existing:
                    raise ValidationError(
                        _("Safe '%s' is already initialized.", op.safe_id.name)
                    )

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.treasury.safe.operation'
                ) or _('New')
        return super().create(vals_list)

    # --- Workflow actions ---

    def action_confirm(self):
        for op in self:
            if op.state != 'draft':
                raise UserError(_("Only draft operations can be confirmed."))
            # Balance check for outgoing operations (neutralized by a forced
            # transfer: the control was already assumed at transfer level)
            if (op.operation_type in ('bank_out', 'other_out')
                    and not self.env.context.get('oski_treasury_force_transfer')):
                if not op.safe_id.allow_negative_balance:
                    if op.safe_id.current_balance < op.amount:
                        if op.safe_id.control_level == 'blocking':
                            raise UserError(
                                _("Insufficient balance in safe '%s'.",
                                  op.safe_id.name)
                            )
            op.state = 'confirmed'

    def action_done(self):
        for op in self:
            if op.state != 'confirmed':
                raise UserError(_("Only confirmed operations can be marked done."))
            op.write({
                'state': 'done',
                'validated_by': self.env.user.id,
            })
            # Mark the safe as initialized
            if op.operation_type == 'initial':
                op.safe_id.is_initialized = True

    def action_cancel(self):
        for op in self:
            if op.state == 'done':
                raise UserError(_("Cannot cancel a done operation."))
            op.state = 'cancel'
