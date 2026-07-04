# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TreasuryTransfer(models.Model):
    _name = 'oski.treasury.transfer'
    _description = 'Treasury Transfer'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    transfer_type = fields.Selection([
        ('cash_to_cash', 'Cash Register -> Cash Register'),
        ('cash_to_safe', 'Cash Register -> Safe'),
        ('safe_to_cash', 'Safe -> Cash Register'),
        ('safe_to_safe', 'Safe -> Safe'),
    ], string='Transfer Type', required=True, tracking=True)
    amount = fields.Monetary(
        string='Amount', required=True, tracking=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Datetime(
        string='Date', required=True, default=fields.Datetime.now,
        tracking=True,
    )
    description = fields.Text(string='Description')

    # --- Sources / Destinations ---
    cash_from_id = fields.Many2one('oski.treasury.cash', string='Source Cash Register')
    cash_to_id = fields.Many2one('oski.treasury.cash', string='Destination Cash Register')
    safe_from_id = fields.Many2one('oski.treasury.safe', string='Source Safe')
    safe_to_id = fields.Many2one('oski.treasury.safe', string='Destination Safe')

    # --- Auto operations ---
    cash_operation_out_id = fields.Many2one(
        'oski.treasury.cash.operation', string='Cash Out Operation', readonly=True,
    )
    cash_operation_in_id = fields.Many2one(
        'oski.treasury.cash.operation', string='Cash In Operation', readonly=True,
    )
    safe_operation_out_id = fields.Many2one(
        'oski.treasury.safe.operation', string='Safe Out Operation', readonly=True,
    )
    safe_operation_in_id = fields.Many2one(
        'oski.treasury.safe.operation', string='Safe In Operation', readonly=True,
    )

    # --- Built-in transfer control ---
    control_checked = fields.Boolean(string='Control Performed', readonly=True)
    control_date = fields.Datetime(string='Control Date', readonly=True)
    control_user_id = fields.Many2one('res.users', string='Controlled By', readonly=True)
    source_balance_before = fields.Monetary(
        string='Source Balance Before', currency_field='currency_id', readonly=True,
    )
    source_balance_after = fields.Monetary(
        string='Source Balance After', currency_field='currency_id',
        compute='_compute_balance_after',
    )
    dest_balance_before = fields.Monetary(
        string='Destination Balance Before', currency_field='currency_id', readonly=True,
    )
    dest_balance_after = fields.Monetary(
        string='Destination Balance After', currency_field='currency_id',
        compute='_compute_balance_after',
    )
    control_warning = fields.Text(
        string='Warnings', compute='_compute_control_warning',
    )
    force_transfer = fields.Boolean(string='Force Transfer')

    # --- State ---
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    user_id = fields.Many2one(
        'res.users', string='Created By', readonly=True,
        default=lambda self: self.env.user,
    )
    validated_by = fields.Many2one('res.users', string='Validated By', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    color = fields.Integer()

    # --- Constraints ---

    @api.constrains('amount')
    def _check_amount(self):
        for tr in self:
            if tr.amount <= 0:
                raise ValidationError(_("The transfer amount must be strictly positive."))

    @api.constrains('transfer_type', 'cash_from_id', 'cash_to_id',
                     'safe_from_id', 'safe_to_id')
    def _check_source_dest(self):
        for tr in self:
            if tr.transfer_type == 'cash_to_cash' and tr.cash_from_id == tr.cash_to_id:
                raise ValidationError(_("The source and destination must be different."))
            if tr.transfer_type == 'safe_to_safe' and tr.safe_from_id == tr.safe_to_id:
                raise ValidationError(_("The source and destination must be different."))

    @api.constrains('company_id', 'cash_from_id', 'cash_to_id',
                     'safe_from_id', 'safe_to_id')
    def _check_legs_company(self):
        for tr in self:
            for leg in (tr.cash_from_id, tr.cash_to_id, tr.safe_from_id, tr.safe_to_id):
                if leg and leg.company_id != tr.company_id:
                    raise ValidationError(
                        _("All transfer legs must belong to the transfer's company.")
                    )

    # --- Compute ---

    @api.depends('source_balance_before', 'dest_balance_before', 'amount')
    def _compute_balance_after(self):
        for tr in self:
            tr.source_balance_after = tr.source_balance_before - tr.amount
            tr.dest_balance_after = tr.dest_balance_before + tr.amount

    @api.depends('source_balance_before', 'amount', 'transfer_type',
                 'cash_from_id', 'safe_from_id')
    def _compute_control_warning(self):
        for tr in self:
            warnings = []
            source = tr.cash_from_id or tr.safe_from_id
            if source and tr.amount:
                balance = source.current_balance
                if balance < tr.amount and not getattr(source, 'allow_negative_balance', False):
                    warnings.append(
                        _("Insufficient balance: %s (available: %s)",
                          source.display_name, balance)
                    )
            tr.control_warning = '\n'.join(warnings) if warnings else False

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.treasury.transfer'
                ) or _('New')
        return super().create(vals_list)

    # --- Helpers ---

    def _get_source_entity(self):
        self.ensure_one()
        if self.transfer_type in ('cash_to_cash', 'cash_to_safe'):
            return self.cash_from_id
        return self.safe_from_id

    def _get_dest_entity(self):
        self.ensure_one()
        if self.transfer_type in ('cash_to_cash', 'safe_to_cash'):
            return self.cash_to_id
        return self.safe_to_id

    def _check_balance_before_transfer(self):
        """Checks the source balance before the transfer"""
        self.ensure_one()
        source = self._get_source_entity()
        if not source:
            return
        if getattr(source, 'state', False) == 'locked':
            raise UserError(
                _("Source '%s' is locked: transfer impossible.",
                  source.display_name)
            )
        balance = source.current_balance
        self.source_balance_before = balance
        dest = self._get_dest_entity()
        if dest:
            self.dest_balance_before = dest.current_balance

        if not self.force_transfer and balance < self.amount:
            if not getattr(source, 'allow_negative_balance', False):
                ctrl = getattr(source, 'control_level', 'blocking')
                if ctrl == 'blocking':
                    raise UserError(
                        _("Insufficient balance in '%s'. Balance: %s, Amount: %s",
                          source.display_name, balance, self.amount)
                    )

        self.write({
            'control_checked': True,
            'control_date': fields.Datetime.now(),
            'control_user_id': self.env.user.id,
        })

    def _create_cash_operations(self):
        """Creates the cash register operations linked to the transfer"""
        self.ensure_one()
        # force_transfer must also neutralize the balance re-check performed
        # by the leg (oski.treasury.cash.operation.action_post).
        Operation = self.env['oski.treasury.cash.operation'].with_context(
            oski_treasury_force_transfer=self.force_transfer,
        )
        category = self.env['oski.treasury.operation.category'].search(
            [('code', '=', 'TRANSFERT')], limit=1,
        )

        # Cash out operation
        if self.transfer_type in ('cash_to_cash', 'cash_to_safe'):
            op_out = Operation.create({
                'cash_id': self.cash_from_id.id,
                'operation_type': 'out',
                'category_id': category.id if category else False,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfer %s to %s",
                                 self.name, self._get_dest_entity().display_name),
                'transfer_id': self.id,
                'is_manual': False,
            })
            op_out.action_post()
            self.cash_operation_out_id = op_out

        # Cash in operation
        if self.transfer_type in ('cash_to_cash', 'safe_to_cash'):
            op_in = Operation.create({
                'cash_id': self.cash_to_id.id,
                'operation_type': 'in',
                'category_id': category.id if category else False,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfer %s from %s",
                                 self.name, self._get_source_entity().display_name),
                'transfer_id': self.id,
                'is_manual': False,
            })
            op_in.action_post()
            self.cash_operation_in_id = op_in

    def _create_safe_operations(self):
        """Creates the safe operations linked to the transfer"""
        self.ensure_one()
        SafeOperation = self.env['oski.treasury.safe.operation'].with_context(
            oski_treasury_force_transfer=self.force_transfer,
        )

        # Safe out operation
        if self.transfer_type in ('safe_to_cash', 'safe_to_safe'):
            op_out = SafeOperation.create({
                'safe_id': self.safe_from_id.id,
                'operation_type': 'other_out',
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfer %s to %s",
                                 self.name, self._get_dest_entity().display_name),
                'transfer_id': self.id,
            })
            op_out.action_confirm()
            op_out.action_done()
            self.safe_operation_out_id = op_out

        # Safe in operation
        if self.transfer_type in ('cash_to_safe', 'safe_to_safe'):
            op_in = SafeOperation.create({
                'safe_id': self.safe_to_id.id,
                'operation_type': 'other_in',
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfer %s from %s",
                                 self.name, self._get_source_entity().display_name),
                'transfer_id': self.id,
            })
            op_in.action_confirm()
            op_in.action_done()
            self.safe_operation_in_id = op_in

    # --- Workflow actions ---

    def action_confirm(self):
        for tr in self:
            if tr.state != 'draft':
                raise UserError(_("Only draft transfers can be confirmed."))
            tr._check_balance_before_transfer()
            tr._create_cash_operations()
            tr._create_safe_operations()
            tr.state = 'confirm'

    def action_done(self):
        for tr in self:
            if tr.state != 'confirm':
                raise UserError(_("Only confirmed transfers can be marked done."))
            tr.write({
                'state': 'done',
                'validated_by': self.env.user.id,
            })

    def action_cancel(self):
        for tr in self:
            if tr.state == 'done':
                raise UserError(_("Cannot cancel a done transfer."))
            # Cancel the linked cash operations
            for op in (tr.cash_operation_out_id, tr.cash_operation_in_id):
                if op and op.state == 'posted':
                    op.action_cancel()
            # Cancel the linked safe operations
            for op in (tr.safe_operation_out_id, tr.safe_operation_in_id):
                if op and op.state == 'done':
                    op.state = 'cancel'
            tr.state = 'cancel'

    def action_draft(self):
        for tr in self:
            if tr.state != 'cancel':
                raise UserError(_("Only cancelled transfers can be reset to draft."))
            tr.write({
                'state': 'draft',
                'control_checked': False,
            })
