# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # --- Cash treasury fields ---
    journal_type = fields.Selection(
        related='journal_id.type', string='Journal Type', readonly=True,
    )
    treasury_operation_id = fields.Many2one(
        'oski.treasury.cash.operation', string='Cash Operation', readonly=True,
        copy=False,
    )
    cash_id = fields.Many2one(
        'oski.treasury.cash', string='Cash Register',
        compute='_compute_cash_id', store=True, readonly=True,
        help='Cash register automatically determined from the journal',
    )

    @api.depends('journal_id', 'company_id')
    def _compute_cash_id(self):
        for payment in self:
            if payment.journal_id and payment.journal_id.type == 'cash':
                cash = self.env['oski.treasury.cash'].search([
                    ('journal_id', '=', payment.journal_id.id),
                    ('state', '=', 'open'),
                    ('company_id', '=', payment.company_id.id),
                ], limit=1)
                payment.cash_id = cash
            else:
                payment.cash_id = False

    def action_post(self):
        """Override to automatically create a cash operation."""
        res = super().action_post()
        for payment in self:
            if payment.treasury_operation_id:
                continue
            if payment.journal_id.type != 'cash':
                continue
            payment._create_treasury_cash_operation()
        return res

    def _create_treasury_cash_operation(self):
        """Creates a cash operation from the payment."""
        self.ensure_one()
        cash = self.cash_id

        if not cash:
            self.message_post(
                body=_("No open cash register found for journal '%s'. "
                       "The cash operation was not created.",
                       self.journal_id.display_name)
            )
            return

        # Determine type and category
        operation_type, category = self._get_cash_operation_type_and_category()
        if not category:
            self.message_post(
                body=_("Treasury category not found. "
                       "The cash operation was not created.")
            )
            return

        # Look for the ongoing closing (optional - non-blocking)
        pending_closing = self.env['oski.treasury.cash.closing'].search([
            ('cash_id', '=', cash.id),
            ('state', 'in', ['draft', 'confirmed']),
        ], order='closing_date desc, closing_number desc', limit=1)

        # Create the operation
        operation = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': operation_type,
            'category_id': category.id,
            'amount': self.amount,
            'date': fields.Datetime.to_datetime(self.date) if self.date else fields.Datetime.now(),
            'partner_id': self.partner_id.id,
            'description': _("Payment %s - %s", self.name or '', self.partner_id.name or ''),
            'reference': self.name,
            'payment_id': self.id,
            'closing_id': pending_closing.id if pending_closing else False,
            'is_manual': False,
        })
        operation.action_post()

        self.treasury_operation_id = operation
        self.message_post(
            body=_("Cash operation created: %s", operation.name)
        )

    def _get_cash_operation_type_and_category(self):
        """Determines the operation type and category based on the payment."""
        self.ensure_one()
        Category = self.env['oski.treasury.operation.category']

        if self.payment_type == 'inbound':
            if self.partner_type == 'customer':
                # Customer collection
                category = Category.search([
                    ('is_customer_payment', '=', True),
                    ('operation_type', 'in', ['in', 'both']),
                ], limit=1)
                return 'in', category
            else:
                # Vendor refund received
                category = Category.search([
                    ('code', '=', 'REFUND_SUPPLIER'),
                ], limit=1)
                return 'in', category
        else:  # outbound
            if self.partner_type == 'supplier':
                # Vendor payment
                category = Category.search([
                    ('is_vendor_payment', '=', True),
                    ('operation_type', 'in', ['out', 'both']),
                ], limit=1)
                return 'out', category
            else:
                # Customer refund
                category = Category.search([
                    ('code', '=', 'REFUND_CUSTOMER'),
                ], limit=1)
                return 'out', category

    def action_cancel(self):
        """Override to cancel the associated cash operation."""
        for payment in self:
            if payment.treasury_operation_id and payment.treasury_operation_id.state == 'posted':
                op = payment.treasury_operation_id
                if op.closing_id and op.closing_id.state == 'validated':
                    raise UserError(
                        _("Cannot cancel this payment: the cash operation "
                          "is part of the validated closing '%s'.",
                          op.closing_id.name)
                    )
                op.action_cancel()
        return super().action_cancel()

    def action_draft(self):
        """Override to handle the reset to draft."""
        for payment in self:
            if payment.treasury_operation_id:
                op = payment.treasury_operation_id
                if op.closing_id and op.closing_id.state == 'validated':
                    raise UserError(
                        _("Cannot reset to draft: the cash operation "
                          "is part of the validated closing '%s'.",
                          op.closing_id.name)
                    )
                if op.closing_id and op.closing_id.state == 'confirmed':
                    raise UserError(
                        _("Cannot reset to draft: the cash operation "
                          "is part of the confirmed closing '%s'. "
                          "Reset the closing to draft first.",
                          op.closing_id.name)
                    )
        res = super().action_draft()
        for payment in self:
            if payment.treasury_operation_id and payment.treasury_operation_id.state == 'posted':
                payment.treasury_operation_id.write({'state': 'draft'})
        return res
