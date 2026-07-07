from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestDashboardTours(HttpCase):
    def test_smoke_tour(self):
        self.start_tour('/odoo', 'oski_dashboard_smoke', login='admin')
