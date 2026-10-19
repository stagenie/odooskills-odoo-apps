# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TreasuryCashClosing(models.Model):
    _name = 'oski.treasury.cash.closing'
    _description = 'Treasury Cash Closing'
    _inherit = ['mail.thread']
    _order = 'closing_date desc, closing_number desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    cash_id = fields.Many2one(
        'oski.treasury.cash', string='Cash Register', required=True,
        ondelete='restrict', tracking=True,
    )
    closing_date = fields.Date(
        string='Closing Date', required=True,
        default=fields.Date.today, tracking=True,
    )
    closing_number = fields.Integer(
        string='Closing Number', default=1,
        help='Sequential number for closings of the same day',
    )
    currency_id = fields.Many2one(
        'res.currency', related='cash_id.currency_id', store=True,
    )
    company_id = fields.Many2one(
        'res.company', related='cash_id.company_id', store=True,
    )

    # --- Balances ---
    balance_start = fields.Monetary(
        string='Starting Balance', currency_field='currency_id',
        readonly=True, copy=False,
        help="Starting balance = actual balance of the last validated closing "
             "of this cash register (frozen at confirmation). Allows chaining "
             "several closings on the same day.",
    )
    total_in = fields.Monetary(
        string='Total In', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    total_out = fields.Monetary(
        string='Total Out', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    balance_end_theoretical = fields.Monetary(
        string='Theoretical Balance', currency_field='currency_id',
        compute='_compute_theoretical_balance', store=True,
    )
    balance_end_real = fields.Monetary(
        string='Actual Balance', currency_field='currency_id',
        tracking=True,
    )
    difference = fields.Monetary(
        string='Difference', currency_field='currency_id',
        compute='_compute_difference', store=True,
    )

    # --- Operations ---
    operation_ids = fields.One2many(
        'oski.treasury.cash.operation', 'closing_id', string='Operations',
    )

    # --- Pending manual operations (formerly oski_treasury_enhanced) ---
    pending_manual_operation_count = fields.Integer(
        string='Pending Operations',
        compute='_compute_pending_manual_operations',
    )

    # --- State ---
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    user_id = fields.Many2one(
        'res.users', string='Created By', readonly=True,
        default=lambda self: self.env.user,
    )
    validated_by = fields.Many2one(
        'res.users', string='Validated By', readonly=True,
    )
    notes = fields.Text(string='Notes')
    adjustment_operation_id = fields.Many2one(
        'oski.treasury.cash.operation', string='Adjustment Operation',
        readonly=True,
    )

    # --- Compute ---

    def _get_previous_validated_closing(self):
        """Last validated closing of the same cash register (excluding self)."""
        self.ensure_one()
        return self.search([
            ('cash_id', '=', self.cash_id.id),
            ('state', '=', 'validated'),
            ('id', '!=', self.id),
        ], order='closing_date desc, closing_number desc, id desc', limit=1)

    def _refresh_balance_start(self):
        """(Re-)freezes the starting balance on the actual balance of the last
        validated closing. Called on creation and confirmation to correctly
        handle several successive closings on the same day."""
        for closing in self:
            last = closing._get_previous_validated_closing()
            closing.balance_start = last.balance_end_real if last else 0.0

    @api.depends('operation_ids.amount', 'operation_ids.operation_type',
                 'operation_ids.state')
    def _compute_totals(self):
        for closing in self:
            posted = closing.operation_ids.filtered(lambda o: o.state == 'posted')
            closing.total_in = sum(
                o.amount for o in posted if o.operation_type == 'in'
            )
            closing.total_out = sum(
                o.amount for o in posted if o.operation_type == 'out'
            )

    @api.depends('balance_start', 'total_in', 'total_out')
    def _compute_theoretical_balance(self):
        for closing in self:
            closing.balance_end_theoretical = (
                closing.balance_start + closing.total_in - closing.total_out
            )

    @api.depends('balance_end_theoretical', 'balance_end_real')
    def _compute_difference(self):
        for closing in self:
            closing.difference = closing.balance_end_real - closing.balance_end_theoretical

    def _compute_pending_manual_operations(self):
        """Counts the draft manual operations of this cash register, whether
        they are linked to this closing or not."""
        Operation = self.env['oski.treasury.cash.operation']
        for closing in self:
            count = Operation.search_count([
                ('cash_id', '=', closing.cash_id.id),
                ('is_manual', '=', True),
                ('state', '=', 'draft'),
            ])
            closing.pending_manual_operation_count = count

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.treasury.cash.closing'
                ) or _('New')
            # Auto-increment closing_number for same day/cash register.
            # The closing_date default is only applied by super().create():
            # we set it here, otherwise an API/shell creation without an
            # explicit date would keep closing_number=1 (duplicate numbers
            # on the same day).
            if vals.get('cash_id'):
                vals.setdefault('closing_date', fields.Date.today())
                existing = self.search_count([
                    ('cash_id', '=', vals['cash_id']),
                    ('closing_date', '=', vals['closing_date']),
                ])
                vals['closing_number'] = existing + 1
        closings = super().create(vals_list)
        closings._refresh_balance_start()
        return closings

    # --- Workflow actions ---

    def action_load_operations(self):
        """Loads all posted operations not linked to a closing into this closing"""
        for closing in self:
            if closing.state != 'draft':
                raise UserError(_("Loading is only possible in draft state."))
            # Operations of an already closed period already carry a closing_id.
            # We therefore load all posted operations NOT YET attached to a
            # closing. This criterion is correct even for several closings on
            # the same day (a date filter would wrongly exclude the operations
            # of the day of the last validated closing).
            operations = self.env['oski.treasury.cash.operation'].search([
                ('cash_id', '=', closing.cash_id.id),
                ('state', '=', 'posted'),
                ('closing_id', '=', False),
            ])
            operations.write({'closing_id': closing.id})

    def action_confirm(self):
        for closing in self:
            if closing.state != 'draft':
                raise UserError(_("Only draft closings can be confirmed."))
            # Freezes the starting balance on the last validated closing at
            # this point in time (handles several closings confirmed out of
            # order).
            closing._refresh_balance_start()
            # Auto-load if no operations
            if not closing.operation_ids:
                closing.action_load_operations()
            closing.state = 'confirmed'

    def action_validate(self):
        for closing in self:
            if closing.state != 'confirmed':
                raise UserError(_("Only confirmed closings can be validated."))
            # Re-freezes the starting balance: if an earlier closing was
            # validated after this one was confirmed, the starting balance
            # must reflect its actual balance (correct chaining of successive
            # closings).
            closing._refresh_balance_start()
            # Create the adjustment operation if there is a difference
            closing._create_adjustment_operation()
            closing.write({
                'state': 'validated',
                'validated_by': self.env.user.id,
            })
            # Update the cash register
            closing.cash_id.write({
                'last_closing_balance': closing.balance_end_real,
                'last_closing_date': fields.Datetime.now(),
            })

    def _create_adjustment_operation(self):
        """Creates an adjustment operation if there is a difference between
        the theoretical and actual balance"""
        self.ensure_one()
        if not self.difference or self.currency_id.is_zero(self.difference):
            return
        if self.adjustment_operation_id:
            return  # Already created

        category = self.env.ref('oski_treasury.category_ajustement', raise_if_not_found=False)
        if not category:
            category = self.env['oski.treasury.operation.category'].search([
                ('code', '=', 'AJUST'),
            ], limit=1)

        if self.difference > 0:
            # Actual balance > theoretical: surplus -> in
            operation_type = 'in'
            amount = self.difference
            desc = _("Closing adjustment %s: surplus of %s", self.name, amount)
        else:
            # Actual balance < theoretical: shortfall -> out
            operation_type = 'out'
            amount = abs(self.difference)
            desc = _("Closing adjustment %s: shortfall of %s", self.name, amount)

        operation = self.env['oski.treasury.cash.operation'].create({
            'cash_id': self.cash_id.id,
            'operation_type': operation_type,
            'category_id': category.id if category else False,
            'amount': amount,
            'date': fields.Datetime.now(),
            'description': desc,
            'closing_id': self.id,
            'is_manual': False,
        })
        operation.action_post()
        self.adjustment_operation_id = operation

    def action_cancel(self):
        for closing in self:
            if closing.state == 'validated':
                raise UserError(_("Cannot cancel a validated closing."))
            # Releases the attached operations: otherwise they would keep this
            # cancelled closing_id and would never be reloaded into a future
            # closing (action_load_operations only takes closing_id=False),
            # while still being counted in the current balance -> permanent
            # discrepancy.
            closing.operation_ids.write({'closing_id': False})
            closing.state = 'cancel'

    # --- Manual operation actions (formerly oski_treasury_enhanced) ---

    def action_validate_all_pending_operations(self):
        """Posts all draft manual operations and attaches them"""
        self.ensure_one()
        operations = self.env['oski.treasury.cash.operation'].search([
            ('cash_id', '=', self.cash_id.id),
            ('is_manual', '=', True),
            ('state', '=', 'draft'),
        ])
        for op in operations:
            op.closing_id = self.id
            op.action_post()

    def action_view_pending_operations(self):
        """Shows all draft manual operations of this cash register"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Draft Operations'),
            'res_model': 'oski.treasury.cash.operation',
            'view_mode': 'list,form',
            'domain': [
                ('cash_id', '=', self.cash_id.id),
                ('is_manual', '=', True),
                ('state', '=', 'draft'),
            ],
        }

    def action_create_manual_operation(self):
        """Creates a manual operation (draft, not linked to the closing).
        It will appear in 'Pending' and will be linked to the closing when it
        is validated."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Manual Operation'),
            'res_model': 'oski.treasury.cash.operation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cash_id': self.cash_id.id,
                'default_is_manual': True,
            },
        }

    def action_print_closing_report(self):
        """Prints the closing report"""
        self.ensure_one()
        report = self.env.ref('oski_treasury.action_report_cash_closing')
        return report.report_action(self)
