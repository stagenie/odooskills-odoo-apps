from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestDashboardTours(HttpCase):
    def test_smoke_tour(self):
        self.start_tour('/odoo', 'oski_dashboard_smoke', login='admin')

    def test_create_widget_tour(self):
        self.start_tour('/odoo', 'oski_dashboard_create_widget', login='admin')

    def test_chart_widget_tour(self):
        """Widget « barres » : toile Chart.js dessinée, puis redessinée à jour."""
        admin = self.env.ref('base.user_admin')
        tag = self.env['res.partner.category'].create({'name': 'DashTourTag'})
        self.env['res.partner'].create([
            {'name': 'Tour P1', 'category_id': [(4, tag.id)]},
            {'name': 'Tour P2', 'category_id': [(4, tag.id)]},
        ])
        dashboard = self.env['oski.dashboard'].with_user(admin).create({'name': 'Tour graphique'})
        self.env['oski.dashboard.widget'].with_user(admin).create({
            'dashboard_id': dashboard.id, 'name': 'Barres tour', 'widget_type': 'bar',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'group_by_field_id': self.env['ir.model.fields']._get('res.partner', 'type').id,
            'domain': f"[('category_id', 'in', [{tag.id}])]",
        })
        self.start_tour('/odoo', 'oski_dashboard_chart', login='admin')
