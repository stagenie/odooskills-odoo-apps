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
        self.assertIsInstance(data['options'], dict)

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

    def test_kpi_non_stored_measure(self):
        """Mesure calculée non stockée (res.currency.rate) : agrégation Python."""
        currency = self.env['res.currency'].sudo().create({
            'name': 'XDS', 'symbol': 'X',
            'rate_ids': [(0, 0, {'name': '2020-01-01', 'rate': 2.0})],
        })
        model_currency = self.env['ir.model']._get('res.currency')
        field_rate = self.env['ir.model.fields']._get('res.currency', 'rate')
        widget = self._make_widget(
            model_id=model_currency.id,
            domain=f"[('id', '=', {currency.id})]",
            measure_field_id=field_rate.id, measure_agg='sum')
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 2.0)

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

    def test_period_this_month(self):
        field_date = self.env['ir.model.fields']._get('res.partner', 'create_date')
        old = self.env['res.partner'].sudo().create(
            {'name': 'Old', 'category_id': [(4, self.tag.id)]})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = create_date - interval '70 days' WHERE id = %s",
            [old.id])
        old.invalidate_recordset()
        widget = self._make_widget(date_field_id=field_date.id, period='this_month')
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 3)  # Old exclu

    def test_delta_previous_period(self):
        field_date = self.env['ir.model.fields']._get('res.partner', 'create_date')
        prev = self.env['res.partner'].sudo().create(
            {'name': 'Prev', 'category_id': [(4, self.tag.id)]})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = date_trunc('month', now()) - interval '10 days' WHERE id = %s",
            [prev.id])
        prev.invalidate_recordset()
        widget = self._make_widget(
            date_field_id=field_date.id, period='this_month', compare_previous=True)
        data = self.env['oski.dashboard.widget'].with_user(self.user).get_widget_data(widget.id)
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['delta_pct'], 200.0)  # 3 vs 1

    def test_previous_window_calendar_aligned(self):
        """Période N-1 calendaire pour mois/trimestre (pas de dérive 31 vs 30/28 jours)."""
        from dateutil.relativedelta import relativedelta
        field_date = self.env['ir.model.fields']._get('res.partner', 'create_date')
        widget = self._make_widget(date_field_id=field_date.id, period='this_month')
        start, stop, prev_start, prev_stop = widget._period_window()
        self.assertEqual(prev_start, start - relativedelta(months=1))
        self.assertEqual(prev_stop, start)
        widget_q = self._make_widget(date_field_id=field_date.id, period='this_quarter')
        start, stop, prev_start, prev_stop = widget_q._period_window()
        self.assertEqual(prev_start, start - relativedelta(months=3))
        self.assertEqual(prev_stop, start)

    def test_period_domain_datetime_utc(self):
        """Bornes datetime converties tz user -> UTC naïf (stockage Odoo)."""
        import pytz
        self.user.sudo().write({'tz': 'America/New_York'})
        field_date = self.env['ir.model.fields']._get('res.partner', 'create_date')
        widget = self._make_widget(date_field_id=field_date.id, period='today')
        widget_as_user = widget.with_user(self.user)
        start, stop, _, _ = widget_as_user._period_window()
        domain = widget_as_user._period_domain(start, stop)
        tz = pytz.timezone('America/New_York')
        expected_start = tz.localize(start).astimezone(pytz.utc).replace(tzinfo=None)
        expected_stop = tz.localize(stop).astimezone(pytz.utc).replace(tzinfo=None)
        self.assertEqual(domain, [
            ('create_date', '>=', expected_start),
            ('create_date', '<', expected_stop),
        ])
