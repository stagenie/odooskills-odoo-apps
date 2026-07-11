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
                parsed = json.loads(dashboard.layout_json or '{}')
            except ValueError:
                raise ValidationError(self.env._("Disposition invalide (JSON attendu)."))
            # JSON valide mais pas un objet (ex. "null", "[]", "42") : le
            # frontend fait toujours JSON.parse(layout_json || "{}") et
            # itère les clés comme un dict de positions — "null" (JSON
            # valide) plante au premier accès côté client.
            if not isinstance(parsed, dict):
                raise ValidationError(self.env._("Disposition invalide (objet JSON attendu)."))

    def save_layout(self, layout_json):
        self.ensure_one()
        self.write({'layout_json': layout_json})
        return True

    def action_toggle_favorite(self):
        """Bascule le dashboard courant dans/hors des favoris de l'appelant.
        Un simple orm.call write() côté client est refusé par
        rule_dashboard_own_write pour un lecteur partagé (accès via
        group_ids) : cette méthode vérifie le droit de LECTURE (accessible
        au propriétaire ET aux lecteurs partagés), puis écrit en sudo — mais
        BORNÉE à l'ajout/retrait de l'UID appelant dans favorite_user_ids,
        jamais à des vals fournis par le client (cf. brief T16-fix M1)."""
        self.ensure_one()
        self.check_access('read')
        uid = self.env.uid
        command = 3 if uid in self.favorite_user_ids.ids else 4
        self.sudo().write({'favorite_user_ids': [(command, uid)]})
        return True
