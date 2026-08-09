from odoo import fields, models


class PartnerBalanceLine(models.TransientModel):
    _name = 'oski.partner.balance.line'
    _description = 'Partner Balance Line'
    _order = 'wizard_id, sequence'

    wizard_id = fields.Many2one(
        'oski.partner.balance.wizard', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, default=0)
    partner_id = fields.Many2one('res.partner', required=True, index=True)
    section = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('net', 'Net'),
    ], required=True)
    date = fields.Date()
    operation_datetime = fields.Datetime()
    journal_id = fields.Many2one('account.journal')
    move_id = fields.Many2one('account.move')
    move_line_id = fields.Many2one('account.move.line')
    name = fields.Char(string='Document')
    ref = fields.Char(string='Reference')
    label = fields.Char(string='Label')
    date_maturity = fields.Date(string='Due Date')
    debit = fields.Monetary()
    credit = fields.Monetary()
    balance = fields.Monetary()
    cumulative = fields.Monetary(string='Running Balance')
    amount_residual = fields.Monetary(string='Amount Due')
    is_opening = fields.Boolean(string='Opening Line')
    is_excluded = fields.Boolean(
        string='Excluded', related='move_id.oski_exclude_from_balance', readonly=False)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    def action_open_move(self):
        """Open the document behind this line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.move_id.display_name,
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
