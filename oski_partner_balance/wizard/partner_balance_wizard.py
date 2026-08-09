from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PartnerBalanceWizard(models.TransientModel):
    _name = 'oski.partner.balance.wizard'
    _description = 'Partner Balance'

    date_from = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(
        required=True, default=lambda self: fields.Date.context_today(self))
    include_opening = fields.Boolean(
        string='Include Opening Balance', default=True,
        help="Add the balance carried forward at the start date as the first "
             "line, and start the running balance from it.")
    partner_ids = fields.Many2many('res.partner', string='Partners')
    scope = fields.Selection([
        ('receivable', 'Customer'),
        ('payable', 'Vendor'),
        ('both', 'Customer and Vendor (two sections)'),
        ('net', 'Netted (single running balance)'),
    ], required=True, default='receivable')
    journal_filter = fields.Selection([
        ('all', 'All journals'),
        ('include', 'Only the selected journals'),
        ('exclude', 'All but the selected journals'),
    ], required=True, default='all')
    journal_ids = fields.Many2many('account.journal', string='Journals')
    target_moves = fields.Selection([
        ('posted', 'Posted entries'),
        ('all', 'All entries'),
    ], required=True, default='posted')
    line_ids = fields.One2many('oski.partner.balance.line', 'wizard_id')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_("The start date must precede the end date."))

    def _options(self):
        """Option dict consumed by oski.partner.balance.engine."""
        self.ensure_one()
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'include_opening': self.include_opening,
            'partner_ids': self.partner_ids.ids,
            'scope': self.scope,
            'journal_filter': self.journal_filter,
            'journal_ids': self.journal_ids.ids,
            'target_moves': self.target_moves,
        }

    def _generate_lines(self):
        """Drop the previous run and materialise a fresh one."""
        self.ensure_one()
        self.line_ids.unlink()
        rows = self.env['oski.partner.balance.engine']._build_rows(self._options())
        return self.env['oski.partner.balance.line'].create(
            [dict(row, wizard_id=self.id) for row in rows])

    def action_view_lines(self):
        self.ensure_one()
        self._generate_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner Balance'),
            'res_model': 'oski.partner.balance.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'create': False, 'search_default_group_partner': 1},
            'target': 'current',
        }

    def action_print_pdf(self):
        self.ensure_one()
        self._generate_lines()
        return self.env.ref(
            'oski_partner_balance.action_report_partner_balance').report_action(self)
