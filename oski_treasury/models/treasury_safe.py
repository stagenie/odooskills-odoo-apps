# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError


class TreasurySafe(models.Model):
    _name = 'oski.treasury.safe'
    _description = 'Treasury Safe'
    _inherit = ['mail.thread']
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
    responsible_ids = fields.Many2many(
        'res.users', 'treasury_safe_user_rel', 'safe_id', 'user_id',
        string='Responsible', required=True,
    )
    user_ids = fields.Many2many(
        'res.users', 'treasury_safe_viewer_rel', 'safe_id', 'user_id',
        string='Authorized Users',
        help="Users authorized to view this safe (in addition to the "
             "responsible users).",
    )
    state = fields.Selection([
        ('active', 'Active'),
        ('locked', 'Locked'),
    ], string='Status', default='active', required=True, tracking=True)

    # --- Balances ---
    current_balance = fields.Monetary(
        string='Current Balance', currency_field='currency_id',
        compute='_compute_current_balance', store=True,
    )
    max_capacity = fields.Monetary(
        string='Maximum Capacity', currency_field='currency_id',
    )
    is_initialized = fields.Boolean(string='Initialized', readonly=True)

    # --- Transfer control ---
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

    # --- Misc ---
    location = fields.Char(string='Location')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    # --- Relations ---
    operation_ids = fields.One2many(
        'oski.treasury.safe.operation', 'safe_id', string='Operations',
    )

    # --- Constraints ---
    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'The safe code must be unique per company.',
    )

    # --- Compute ---

    @api.depends('operation_ids.amount', 'operation_ids.operation_type',
                 'operation_ids.state')
    def _compute_current_balance(self):
        for safe in self:
            done_ops = safe.operation_ids.filtered(lambda o: o.state == 'done')
            balance = 0.0
            for op in done_ops:
                balance += op._signed_amount()
            safe.current_balance = balance

    def _compute_display_name(self):
        for safe in self:
            safe.display_name = f"[{safe.code}] {safe.name}"

    # --- ORM lock: safe responsibles (D2 hardening, lesson v15
    # safe_access_fix -- a view-level readonly is not enough). ---

    def _check_responsible_ids_lock(self):
        if self.env.su or self.env.user.has_group(
                'oski_treasury.group_treasury_safe_admin'):
            return
        raise AccessError(
            _("Only Safe Administrators may change safe responsibles.")
        )

    @api.model_create_multi
    def create(self, vals_list):
        if any('responsible_ids' in vals for vals in vals_list):
            self._check_responsible_ids_lock()
        return super().create(vals_list)

    def write(self, vals):
        if 'responsible_ids' in vals:
            self._check_responsible_ids_lock()
        return super().write(vals)

    # --- Actions ---

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_unlock(self):
        self.write({'state': 'active'})

    def action_view_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operations - %s', self.name),
            'res_model': 'oski.treasury.safe.operation',
            'view_mode': 'list,form',
            'domain': [('safe_id', '=', self.id)],
            'context': {'default_safe_id': self.id},
        }
