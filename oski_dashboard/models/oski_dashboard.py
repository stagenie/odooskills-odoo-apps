import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OskiDashboard(models.Model):
    _name = 'oski.dashboard'
    _description = 'Tableau de bord'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', string='Propriétaire', required=True, index=True,
        default=lambda self: self.env.user)
    group_ids = fields.Many2many('res.groups', string='Partagé avec (lecture)')
    company_id = fields.Many2one('res.company', string='Société')
    favorite_user_ids = fields.Many2many(
        'res.users', 'oski_dashboard_favorite_rel', 'dashboard_id', 'user_id',
        string='Favori de')
    layout_json = fields.Text(string='Disposition', default='{}')
    refresh_interval = fields.Integer(
        string='Rafraîchissement (s)', default=0,
        help="0 = manuel. Sinon, re-lecture automatique toutes les N secondes.")
    widget_ids = fields.One2many('oski.dashboard.widget', 'dashboard_id', string='Widgets')

    @api.constrains('layout_json')
    def _check_layout_json(self):
        for dashboard in self:
            try:
                json.loads(dashboard.layout_json or '{}')
            except ValueError:
                raise ValidationError(self.env._("Disposition invalide (JSON attendu)."))

    def save_layout(self, layout_json):
        self.ensure_one()
        self.write({'layout_json': layout_json})
        return True
