# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class TreasuryCash(models.Model):
    _name = 'oski.treasury.cash'
    _description = 'Treasury Cash Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        'account.journal', string='Cash Journal', required=True,
        domain="[('type', '=', 'cash')]",
        tracking=True,
    )
    responsible_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True,
    )
    user_ids = fields.Many2many(
        'res.users', 'treasury_cash_user_rel', 'cash_id', 'user_id',
        string='Authorized Users',
    )
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('locked', 'Locked'),
    ], string='Status', default='open', required=True, tracking=True)

    # --- Balances ---
    current_balance = fields.Monetary(
        string='Current Balance', currency_field='currency_id',
        compute='_compute_current_balance', store=True,
    )
    last_closing_balance = fields.Monetary(
        string='Last Closing Balance', currency_field='currency_id',
        readonly=True,
    )
    last_closing_date = fields.Datetime(string='Last Closing Date', readonly=True)
    opening_date = fields.Date(string='Opening Date', default=fields.Date.today)

    # --- Settings ---
    max_amount = fields.Monetary(
        string='Maximum Amount', currency_field='currency_id',
    )
    require_closing = fields.Boolean(string='Closing Required')
    auto_close_days = fields.Integer(string='Closing Deadline (days)', default=1)
    location = fields.Char(string='Location')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color')

    # --- Transfer control (formerly oski_treasury_transfer_control) ---
    allow_negative_balance = fields.Boolean(
        string='Allow Negative Balance', default=False,
    )
    min_balance = fields.Monetary(
        string='Minimum Balance', currency_field='currency_id',
    )
    control_level = fields.Selection([
        ('none', 'None'),
        ('warning', 'Warning'),
        ('blocking', 'Blocking'),
    ], string='Control Level', default='blocking')

    # --- Relations ---
    operation_ids = fields.One2many(
        'oski.treasury.cash.operation', 'cash_id', string='Operations',
    )
    closing_ids = fields.One2many(
        'oski.treasury.cash.closing', 'cash_id', string='Closings',
    )

    # --- Computed ---
    operation_count = fields.Integer(
        string='Operation Count', compute='_compute_counts',
    )
    closing_count = fields.Integer(
        string='Closing Count', compute='_compute_counts',
    )
    days_since_closing = fields.Integer(
        string='Days Since Closing', compute='_compute_days_since_closing',
        store=True,
    )
    is_closing_late = fields.Boolean(
        string='Closing Late', compute='_compute_days_since_closing',
        store=True,
    )
    has_pending_closing = fields.Boolean(
        string='Closing In Progress', compute='_compute_has_pending_closing',
        store=True,
    )
    balance_in_motion = fields.Monetary(
        string='Balance In Motion', currency_field='currency_id',
        compute='_compute_balance_in_motion',
        help="Net amount of posted operations already attached to an ongoing "
             "closing (draft/confirmed), not yet validated. Indicates the "
             "part of the current balance that will be frozen when the "
             "closing is validated.",
    )

    # --- SQL constraints (v19) ---
    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'The cash register code must be unique per company.',
    )
    _journal_company_uniq = models.Constraint(
        'UNIQUE(journal_id, company_id)',
        'This journal is already used by another cash register.',
    )

    # --- Compute methods ---

    @api.depends('operation_ids.state', 'operation_ids.amount',
                 'operation_ids.operation_type', 'operation_ids.closing_id',
                 'last_closing_balance')
    def _compute_current_balance(self):
        for cash in self:
            # Only posted operations NOT included in a validated closing
            posted_ops = cash.operation_ids.filtered(
                lambda o: o.state == 'posted'
                and (not o.closing_id or o.closing_id.state != 'validated')
            )
            balance = cash.last_closing_balance
            for op in posted_ops:
                if op.operation_type == 'in':
                    balance += op.amount
                else:
                    balance -= op.amount
            cash.current_balance = balance

    def _compute_counts(self):
        for cash in self:
            cash.operation_count = len(cash.operation_ids)
            cash.closing_count = len(cash.closing_ids)

    @api.depends('last_closing_date', 'require_closing', 'auto_close_days')
    def _compute_days_since_closing(self):
        now = fields.Datetime.now()
        for cash in self:
            if cash.last_closing_date:
                delta = now - cash.last_closing_date
                cash.days_since_closing = delta.days
            else:
                cash.days_since_closing = 0
            cash.is_closing_late = (
                cash.require_closing
                and cash.days_since_closing > cash.auto_close_days
            )

    def _cron_update_days_since_closing(self):
        """Daily cron: refresh days_since_closing / is_closing_late.

        Both fields are stored computes depending only on
        last_closing_date/require_closing/auto_close_days: they never
        change on their own as days pass with no write on the register,
        so without this cron they silently go stale (a register closed
        10 days ago keeps showing 'Days Since Closing = 0' until its next
        unrelated write). Locked registers are excluded: once locked they
        are frozen and their closing lateness no longer matters.
        """
        cashes = self.search([('state', '!=', 'locked')])
        cashes._compute_days_since_closing()
        cashes.flush_recordset(['days_since_closing', 'is_closing_late'])

    @api.depends('closing_ids.state')
    def _compute_has_pending_closing(self):
        for cash in self:
            cash.has_pending_closing = bool(cash.closing_ids.filtered(
                lambda c: c.state in ('draft', 'confirmed')
            ))

    @api.depends('closing_ids.state', 'closing_ids.operation_ids.state',
                 'closing_ids.operation_ids.amount',
                 'closing_ids.operation_ids.operation_type')
    def _compute_balance_in_motion(self):
        for cash in self:
            pending = cash.closing_ids.filtered(
                lambda c: c.state in ('draft', 'confirmed')
            )
            balance = 0.0
            for op in pending.operation_ids.filtered(lambda o: o.state == 'posted'):
                if op.operation_type == 'in':
                    balance += op.amount
                else:
                    balance -= op.amount
            cash.balance_in_motion = balance

    # --- Display ---

    def _compute_display_name(self):
        for cash in self:
            cash.display_name = f"[{cash.code}] {cash.name}"

    # --- Python constraints ---

    @api.constrains('max_amount')
    def _check_max_amount(self):
        for cash in self:
            if cash.max_amount and cash.max_amount < 0:
                raise ValidationError(
                    _("The maximum amount cannot be negative.")
                )

    @api.constrains('min_balance', 'allow_negative_balance')
    def _check_min_balance(self):
        for cash in self:
            if not cash.allow_negative_balance and cash.min_balance < 0:
                raise ValidationError(
                    _("The minimum balance cannot be negative if negative "
                      "balance is not allowed.")
                )

    # --- ORM lock: authorized users/responsible (D2 hardening, same
    # lesson as the safe's responsible_ids -- a view-level readonly is
    # not enough). Reserved to Treasury Managers. ---

    def _check_user_assignment_lock(self):
        if self.env.su or self.env.user.has_group(
                'oski_treasury.group_treasury_manager'):
            return
        raise AccessError(
            _("Only Treasury Managers may assign cash register users/responsible.")
        )

    @api.model_create_multi
    def create(self, vals_list):
        if any('user_ids' in vals or 'responsible_id' in vals for vals in vals_list):
            self._check_user_assignment_lock()
        return super().create(vals_list)

    def write(self, vals):
        if 'user_ids' in vals or 'responsible_id' in vals:
            self._check_user_assignment_lock()
        return super().write(vals)

    # --- Actions ---

    def action_open(self):
        self.write({'state': 'open'})

    def action_close_temporary(self):
        self.write({'state': 'closed'})

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_view_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operations - %s', self.name),
            'res_model': 'oski.treasury.cash.operation',
            'view_mode': 'list,form',
            'domain': [('cash_id', '=', self.id)],
            'context': {'default_cash_id': self.id},
        }

    def action_view_closings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Closings - %s', self.name),
            'res_model': 'oski.treasury.cash.closing',
            'view_mode': 'list,form',
            'domain': [('cash_id', '=', self.id)],
            'context': {'default_cash_id': self.id},
        }

    def action_view_pending_closings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ongoing Closings - %s', self.name),
            'res_model': 'oski.treasury.cash.closing',
            'view_mode': 'list,form',
            'domain': [('cash_id', '=', self.id), ('state', 'in', ('draft', 'confirmed'))],
            'context': {'default_cash_id': self.id},
        }

    def action_open_last_closing(self):
        """Opens the last closing (ongoing or validated) in form view"""
        self.ensure_one()
        # Priority: ongoing closing (draft/confirmed), otherwise last validated
        closing = self.closing_ids.filtered(
            lambda c: c.state in ('draft', 'confirmed')
        ).sorted('closing_date', reverse=True)[:1]
        if not closing:
            closing = self.closing_ids.filtered(
                lambda c: c.state == 'validated'
            ).sorted('closing_date', reverse=True)[:1]
        if not closing:
            # No closing yet -> create a new one
            return self.action_create_closing()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Closing - %s', self.name),
            'res_model': 'oski.treasury.cash.closing',
            'view_mode': 'form',
            'res_id': closing.id,
        }

    def action_print_last_closing(self):
        """Prints the report of the last validated closing"""
        self.ensure_one()
        closing = self.closing_ids.filtered(
            lambda c: c.state == 'validated'
        ).sorted('closing_date', reverse=True)[:1]
        if not closing:
            # If none validated, take the last confirmed
            closing = self.closing_ids.filtered(
                lambda c: c.state == 'confirmed'
            ).sorted('closing_date', reverse=True)[:1]
        if not closing:
            raise UserError(_("No closing to print for this cash register."))
        report = self.env.ref('oski_treasury.action_report_cash_closing')
        return report.report_action(closing)

    def action_create_closing(self):
        self.ensure_one()
        closing = self.env['oski.treasury.cash.closing'].create({
            'cash_id': self.id,
            'closing_date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Closing'),
            'res_model': 'oski.treasury.cash.closing',
            'view_mode': 'form',
            'res_id': closing.id,
        }
