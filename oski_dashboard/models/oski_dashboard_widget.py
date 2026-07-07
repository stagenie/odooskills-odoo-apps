from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class OskiDashboardWidget(models.Model):
    _name = 'oski.dashboard.widget'
    _description = 'Widget de tableau de bord'
    _order = 'id'

    dashboard_id = fields.Many2one(
        'oski.dashboard', required=True, index=True, ondelete='cascade')
    name = fields.Char(string='Titre', required=True)
    widget_type = fields.Selection(
        selection=[
            ('kpi', 'KPI'), ('bar', 'Barres'), ('line', 'Lignes'), ('area', 'Aires'),
            ('pie', 'Camembert'), ('donut', 'Donut'), ('list', 'Liste'),
            ('gauge', 'Jauge'), ('text', 'Texte'),
        ], required=True, default='kpi')
    model_id = fields.Many2one('ir.model', string='Modèle', ondelete='cascade')
    model_name = fields.Char(related='model_id.model')
    domain = fields.Char(string='Filtre', default='[]')
    group_by_field_id = fields.Many2one(
        'ir.model.fields', string='Grouper par',
        domain="[('model_id', '=', model_id), ('store', '=', True)]")
    group_by_granularity = fields.Selection(
        selection=[('day', 'Jour'), ('week', 'Semaine'), ('month', 'Mois'),
                   ('quarter', 'Trimestre'), ('year', 'Année')], default='month')
    measure_field_id = fields.Many2one(
        'ir.model.fields', string='Mesure',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('integer', 'float', 'monetary')), ('store', '=', True)]",
        help="Vide = comptage d'enregistrements.")
    measure_agg = fields.Selection(
        selection=[('sum', 'Somme'), ('avg', 'Moyenne'), ('min', 'Min'), ('max', 'Max')],
        string='Agrégat', default='sum')
    date_field_id = fields.Many2one(
        'ir.model.fields', string='Champ de période',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime')), ('store', '=', True)]")
    period = fields.Selection(
        selection=[
            ('today', "Aujourd'hui"), ('this_week', 'Cette semaine'),
            ('this_month', 'Ce mois'), ('this_quarter', 'Ce trimestre'),
            ('this_year', 'Cette année'), ('last_7d', '7 derniers jours'),
            ('last_30d', '30 derniers jours'), ('last_90d', '90 derniers jours'),
            ('last_12m', '12 derniers mois'), ('all', 'Tout'),
        ], string='Période', default='all')
    compare_previous = fields.Boolean(string='Comparer à la période précédente')
    limit = fields.Integer(string='Top N', default=0)
    options = fields.Text(string='Options', default='{}')

    @api.constrains('domain', 'model_id')
    def _check_domain(self):
        for widget in self:
            if not widget.model_id:
                continue
            try:
                dom = safe_eval(widget.domain or '[]')
                if not isinstance(dom, list):
                    raise ValueError()
                self.env[widget.model_id.model]._search(dom, limit=1)
            except ValidationError:
                raise
            except Exception:
                raise ValidationError(
                    self.env._("Filtre invalide pour le modèle %s.", widget.model_id.model))
