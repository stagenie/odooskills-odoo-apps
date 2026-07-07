from odoo.tests import TransactionCase, new_test_user


class TestWidgetData(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='dash_data')
        cls.dash = cls.env['oski.dashboard'].with_user(cls.user).create({'name': 'Test'})
        cls.model_partner = cls.env['ir.model']._get('res.partner')
        cls.field_color = cls.env['ir.model.fields']._get('res.partner', 'color')
        cls.field_company_type = cls.env['ir.model.fields']._get('res.partner', 'company_type')
        cls.tag = cls.env['res.partner.category'].sudo().create({'name': 'DashTag'})
        cls.partners = cls.env['res.partner'].sudo().create([
            {'name': 'P1', 'color': 2, 'is_company': True, 'category_id': [(4, cls.tag.id)]},
            {'name': 'P2', 'color': 3, 'is_company': True, 'category_id': [(4, cls.tag.id)]},
            {'name': 'P3', 'color': 5, 'is_company': False, 'category_id': [(4, cls.tag.id)]},
        ])

    def _make_widget(self, **vals):
        base = {'dashboard_id': self.dash.id, 'name': 'W', 'widget_type': 'kpi',
                'model_id': self.model_partner.id,
                'domain': f"[('category_id', 'in', [{self.tag.id}])]"}
        base.update(vals)
        return self.env['oski.dashboard.widget'].with_user(self.user).create(base)

    def test_kpi_count(self):
        widget = self._make_widget()
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['widget_type'], 'kpi')

    def test_kpi_sum(self):
        widget = self._make_widget(measure_field_id=self.field_color.id, measure_agg='sum')
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 10)

    def test_group_by_selection(self):
        widget = self._make_widget(widget_type='bar', group_by_field_id=self.field_company_type.id)
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(sorted(data['values']), [1, 2])
        self.assertEqual(len(data['labels']), 2)

    def test_top_n_limit(self):
        field_id = self.env['ir.model.fields']._get('res.partner', 'id')
        widget = self._make_widget(widget_type='list', group_by_field_id=field_id.id, limit=2)
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(len(data['labels']), 2)

    def test_record_rules_applied(self):
        """Argument marketing : un user restreint voit des chiffres restreints."""
        self.env['ir.rule'].sudo().create({
            'name': 'test partner restrict',
            'model_id': self.model_partner.id,
            'domain_force': "[('is_company', '=', True)]",
            'groups': [(4, self.env.ref('base.group_user').id)],
        })
        widget = self._make_widget()
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 2)
