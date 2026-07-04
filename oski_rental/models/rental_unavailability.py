from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RentalUnavailability(models.Model):
    _name = 'oski.rental.unavailability'
    _description = 'Indisponibilité de ressource'
    _order = 'date_start desc'

    asset_id = fields.Many2one(
        'oski.rental.asset', string='Ressource', required=True, ondelete='cascade')
    date_start = fields.Datetime(string='Du', required=True)
    date_end = fields.Datetime(string='Au', required=True)
    reason = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('immobilization', 'Immobilisation'),
        ('other', 'Autre'),
    ], string='Motif', required=True, default='maintenance')
    note = fields.Text(string='Note')
    company_id = fields.Many2one(related='asset_id.company_id', store=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end <= record.date_start:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début.")
