# -*- coding: utf-8 -*-
from odoo import models, fields


class TreasuryOperationCategory(models.Model):
    _name = 'oski.treasury.operation.category'
    _description = 'Treasury Operation Category'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    operation_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out'),
        ('both', 'Both'),
    ], string='Type', required=True, default='both')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_customer_payment = fields.Boolean(string='Customer Payment')
    is_vendor_payment = fields.Boolean(string='Vendor Payment')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    debit_account_id = fields.Many2one(
        'account.account', string='Debit Account',
        domain="[('active', '=', True)]",
        help="Account debited by the accounting entry. If empty, uses the "
             "default account configured in Treasury Settings.",
    )
    credit_account_id = fields.Many2one(
        'account.account', string='Credit Account',
        domain="[('active', '=', True)]",
        help="Account credited by the accounting entry. If empty, uses the "
             "default account configured in Treasury Settings.",
    )

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'The category code must be unique per company.',
    )
