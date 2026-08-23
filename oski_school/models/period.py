from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SchoolPeriod(models.Model):
    _name = 'oski.school.period'
    _description = 'School Period'
    _order = 'date_start desc, id desc'

    name = fields.Char(required=True)
    code = fields.Char(required=True, size=16)
    period_type = fields.Selection([
        ('year', 'School year'),
        ('semester', 'Semester'),
        ('session', 'Session'),
    ], required=True, default='year')
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed'),
    ], default='draft', required=True, copy=False, index=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    term_ids = fields.One2many('oski.school.term', 'period_id', string='Terms')
    is_current = fields.Boolean(compute='_compute_is_current')

    _code_company_uniq = models.Constraint(
        'UNIQUE (code, company_id)', 'The period code must be unique per company.')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_start >= period.date_end:
                raise ValidationError(self.env._('The start date must be before the end date.'))

    @api.depends('state', 'date_start', 'date_end')
    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for period in self:
            period.is_current = (
                period.state == 'open' and period.date_start <= today <= period.date_end)

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})

    @api.model
    def get_current(self, company, period_type):
        today = fields.Date.context_today(self)
        return self.search([
            ('company_id', '=', company.id), ('period_type', '=', period_type),
            ('state', '=', 'open'), ('date_start', '<=', today), ('date_end', '>=', today),
        ], order='date_start desc', limit=1)


class SchoolTerm(models.Model):
    _name = 'oski.school.term'
    _description = 'School Term'
    _order = 'period_id, sequence, id'

    period_id = fields.Many2one('oski.school.period', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    company_id = fields.Many2one(related='period_id.company_id', store=True)

    @api.constrains('date_start', 'date_end', 'period_id')
    def _check_dates(self):
        for term in self:
            if term.date_start >= term.date_end:
                raise ValidationError(self.env._('The term start date must be before its end date.'))
            if term.date_start < term.period_id.date_start or term.date_end > term.period_id.date_end:
                raise ValidationError(self.env._('A term must stay inside its period.'))
