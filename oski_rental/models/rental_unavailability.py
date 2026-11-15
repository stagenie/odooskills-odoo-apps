from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RentalUnavailability(models.Model):
    _name = 'oski.rental.unavailability'
    _description = 'Resource Unavailability'
    _order = 'date_start desc'

    asset_id = fields.Many2one(
        'oski.rental.asset', string='Resource', required=True, ondelete='cascade')
    date_start = fields.Datetime(string='From', required=True)
    date_end = fields.Datetime(string='To', required=True)
    reason = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('immobilization', 'Downtime'),
        ('other', 'Other'),
    ], string='Reason', required=True, default='maintenance')
    note = fields.Text(string='Note')
    company_id = fields.Many2one(related='asset_id.company_id', store=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end <= record.date_start:
                raise ValidationError(
                    self.env._("The end date must be after the start date."))
