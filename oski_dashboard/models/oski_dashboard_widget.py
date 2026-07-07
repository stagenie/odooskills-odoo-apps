import json
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

# Plafond du repli Python : quand le group by (ou la mesure) porte sur un champ
# non stocké, l'agrégation se fait en Python sur un search() — on borne le
# nombre d'enregistrements chargés pour éviter un parcours illimité.
NON_STORED_MAX_RECORDS = 5000


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

    @api.model
    def get_widget_data(self, widget_id, global_filters=None, drill_path=None):
        widget = self.browse(widget_id)
        widget.check_access('read')
        # Contrat de payload : options est un dict (le frontend ne parse pas de JSON).
        try:
            options = json.loads(widget.options or '{}')
        except ValueError:
            options = {}
        if not isinstance(options, dict):
            options = {}
        payload = {
            'name': widget.name,
            'widget_type': widget.widget_type,
            'options': options,
            'labels': [], 'values': [], 'total': 0, 'delta_pct': None,
        }
        if not widget.model_id:
            return payload
        Model = self.env[widget.model_id.model]
        domain = safe_eval(widget.domain or '[]')
        domain += widget._extra_filters_domain(global_filters or [])
        start, stop, prev_start, prev_stop = widget._period_window()
        current_domain = list(domain)
        if start:
            current_domain += widget._period_domain(start, stop)
        data = widget._aggregate(Model, current_domain)
        payload.update(data)
        if widget.compare_previous and prev_start:
            prev = widget._aggregate(Model, domain + widget._period_domain(prev_start, prev_stop))
            if prev['total']:
                payload['delta_pct'] = round(
                    100.0 * (payload['total'] - prev['total']) / abs(prev['total']), 1)
        return payload

    def _extra_filters_domain(self, global_filters):
        """Hook : le module pro ajoute le cross-filtering ici."""
        self.ensure_one()
        return []

    def _period_window(self):
        self.ensure_one()
        if not self.date_field_id or not self.period or self.period == 'all':
            return None, None, None, None
        today = fields.Date.context_today(self)
        start_of_day = datetime.combine(today, time.min)
        if self.period == 'today':
            start = start_of_day
            stop = start + timedelta(days=1)
        elif self.period == 'this_week':
            start = start_of_day - timedelta(days=today.weekday())
            stop = start + timedelta(weeks=1)
        elif self.period == 'this_month':
            start = start_of_day.replace(day=1)
            stop = start + relativedelta(months=1)
        elif self.period == 'this_quarter':
            quarter_month = 3 * ((today.month - 1) // 3) + 1
            start = start_of_day.replace(month=quarter_month, day=1)
            stop = start + relativedelta(months=3)
        elif self.period == 'this_year':
            start = start_of_day.replace(month=1, day=1)
            stop = start + relativedelta(years=1)
        elif self.period == 'last_7d':
            stop = start_of_day + timedelta(days=1)
            start = stop - timedelta(days=7)
        elif self.period == 'last_30d':
            stop = start_of_day + timedelta(days=1)
            start = stop - timedelta(days=30)
        elif self.period == 'last_90d':
            stop = start_of_day + timedelta(days=1)
            start = stop - timedelta(days=90)
        else:  # last_12m
            stop = start_of_day + timedelta(days=1)
            start = stop - relativedelta(months=12)
        length = stop - start
        return start, stop, start - length, start

    def _period_domain(self, start, stop):
        self.ensure_one()
        # Lecture de métadonnées (nom/type du champ de date) en sudo, comme
        # measure_field_id/group_by_field_id dans _aggregate : ir.model.fields
        # n'est lisible que par group_erp_manager, sans lien avec les droits
        # d'accès aux données métier ci-dessus.
        date_field = self.date_field_id.sudo()
        field_name = date_field.name
        if date_field.ttype == 'date':
            start, stop = start.date(), stop.date()
        return [(field_name, '>=', start), (field_name, '<', stop)]

    def _aggregate(self, Model, domain):
        self.ensure_one()
        # Lecture des métadonnées (nom/type du champ) en sudo : ir.model.fields
        # n'est lisible que par group_erp_manager (cf. base/security/ir.model.access.csv),
        # ce qui n'a rien à voir avec les droits d'accès aux données métier ci-dessous.
        measure_field = self.measure_field_id.sudo()
        measure_stored = not measure_field or Model._fields[measure_field.name].store
        aggregate = ('__count' if not measure_field
                     else f'{measure_field.name}:{self.measure_agg}')
        if not self.group_by_field_id:
            if not measure_stored:
                # Mesure calculée non stockée : _read_group ne sait pas la traduire
                # en SQL, agrégation Python plafonnée (droits du user courant).
                records = Model.search(domain, limit=NON_STORED_MAX_RECORDS)
                values = [v or 0 for v in records.mapped(measure_field.name)]
                return {'labels': [], 'values': [], 'total': self._python_aggregate(values)}
            groups = Model._read_group(domain, [], [aggregate])
            total = groups[0][0] if groups else 0
            return {'labels': [], 'values': [], 'total': total or 0}

        group_by_field = self.group_by_field_id.sudo()
        fname = group_by_field.name
        odoo_field = Model._fields[fname]
        if odoo_field.store and measure_stored:
            groupby = fname
            if odoo_field.type in ('date', 'datetime'):
                groupby = f'{groupby}:{self.group_by_granularity or "month"}'
            groups = Model._read_group(domain, [groupby], [aggregate])
            pairs = [(self._format_group_label(key), value or 0) for key, value in groups]
        else:
            # Champs calculés non stockés (ex. res.partner.company_type) : _read_group
            # ne sait pas les traduire en SQL, on agrège donc en Python. search()
            # applique déjà les règles d'accès de l'utilisateur courant (pas de sudo).
            pairs = self._aggregate_non_stored(Model, domain, odoo_field, measure_field)

        labels = [p[0] for p in pairs]
        values = [p[1] for p in pairs]
        if self.limit:
            top = sorted(zip(labels, values), key=lambda p: p[1], reverse=True)[:self.limit]
            labels = [p[0] for p in top]
            values = [p[1] for p in top]
        total = sum(v for v in values if isinstance(v, (int, float)))
        return {'labels': labels, 'values': values, 'total': total}

    def _aggregate_non_stored(self, Model, domain, group_field, measure_field):
        # Le group by porte sur un champ non stocké : agrégation en Python,
        # search() plafonné pour ne pas charger un volume illimité en mémoire.
        records = Model.search(domain, limit=NON_STORED_MAX_RECORDS)
        ids_by_key = {}
        order = []
        for record in records:
            key = record[group_field.name]
            if key not in ids_by_key:
                ids_by_key[key] = []
                order.append(key)
            ids_by_key[key].append(record.id)
        selection_map = {}
        if group_field.type == 'selection' and isinstance(group_field.selection, list):
            selection_map = dict(group_field.selection)
        pairs = []
        for key in order:
            group_records = Model.browse(ids_by_key[key])
            if not measure_field:
                value = len(group_records)
            else:
                values = [v or 0 for v in group_records.mapped(measure_field.name)]
                value = self._python_aggregate(values)
            label = selection_map.get(key) or self._format_group_label(key)
            pairs.append((label, value))
        return pairs

    def _python_aggregate(self, values):
        if not values:
            return 0
        if self.measure_agg == 'avg':
            return sum(values) / len(values)
        if self.measure_agg == 'min':
            return min(values)
        if self.measure_agg == 'max':
            return max(values)
        return sum(values)

    def _format_group_label(self, key):
        if key is None or key is False:
            return self.env._("Indéfini")
        if isinstance(key, models.BaseModel):
            return key.display_name or self.env._("Indéfini")
        return str(key)
