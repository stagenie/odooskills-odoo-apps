from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user


class TestDashboardModels(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = new_test_user(cls.env, login='dash_a')
        cls.user_b = new_test_user(cls.env, login='dash_b')
        cls.manager = new_test_user(
            cls.env, login='dash_mgr',
            groups='base.group_user,oski_dashboard.group_dashboard_manager')
        cls.dash_a = cls.env['oski.dashboard'].with_user(cls.user_a).create({'name': 'Ventes A'})

    def test_owner_default(self):
        self.assertEqual(self.dash_a.user_id, self.user_a)

    def test_other_user_cannot_read(self):
        with self.assertRaises(AccessError):
            self.dash_a.with_user(self.user_b).name  # noqa: B018

    def test_shared_group_can_read(self):
        group = self.env['res.groups'].sudo().create({'name': 'Equipe Test Dash'})
        self.dash_a.sudo().group_ids = group
        self.user_b.sudo().write({'group_ids': [(4, group.id)]})
        self.assertEqual(self.dash_a.with_user(self.user_b).name, 'Ventes A')
        with self.assertRaises(AccessError):
            self.dash_a.with_user(self.user_b).write({'name': 'X'})

    def test_manager_reads_all(self):
        self.assertEqual(self.dash_a.with_user(self.manager).name, 'Ventes A')

    def test_widget_invalid_domain_rejected(self):
        model_partner = self.env['ir.model']._get('res.partner')
        with self.assertRaises(ValidationError):
            self.env['oski.dashboard.widget'].with_user(self.user_a).create({
                'dashboard_id': self.dash_a.id, 'name': 'Bad', 'widget_type': 'kpi',
                'model_id': model_partner.id, 'domain': "[('no_such_field', '=', 1)]",
            })

    def test_widget_cascade_delete(self):
        model_partner = self.env['ir.model']._get('res.partner')
        w = self.env['oski.dashboard.widget'].with_user(self.user_a).create({
            'dashboard_id': self.dash_a.id, 'name': 'Clients', 'widget_type': 'kpi',
            'model_id': model_partner.id,
        })
        self.dash_a.with_user(self.user_a).unlink()
        self.assertFalse(w.exists())

    def test_save_layout(self):
        self.dash_a.with_user(self.user_a).save_layout('{"1": {"x": 0, "y": 0, "w": 4, "h": 2}}')
        self.assertIn('"w": 4', self.dash_a.layout_json)
