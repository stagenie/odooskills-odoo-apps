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

    def test_layout_json_non_dict_rejected(self):
        # m3 : "null"/"[1,2,3]" sont du JSON valide mais pas un objet — le
        # frontend fait toujours JSON.parse(layout_json || "{}") et itère
        # les clés comme des positions, un non-dict plante côté client.
        with self.assertRaises(ValidationError):
            self.dash_a.with_user(self.user_a).write({'layout_json': 'null'})
        with self.assertRaises(ValidationError):
            self.dash_a.with_user(self.user_a).write({'layout_json': '[1, 2, 3]'})

    def test_get_available_models_standard_user(self):
        # B1 : l'éditeur de widget interroge ir.model via un proxy sudo —
        # un utilisateur standard (group_user seul, sans group_erp_manager)
        # ne doit jamais lever AccessError (ACL core ir.model = 0,0,0,0).
        models = self.env['oski.dashboard.widget'].with_user(
            self.user_a).get_available_models()
        self.assertTrue(any(m['model'] == 'res.partner' for m in models))

    def test_get_model_fields_standard_user(self):
        model_partner = self.env['ir.model']._get('res.partner')
        fields_data = self.env['oski.dashboard.widget'].with_user(
            self.user_a).get_model_fields(model_partner.id)
        self.assertTrue(any(f['name'] == 'name' for f in fields_data))

    def test_metadata_proxies_denied_to_portal(self):
        # Durcissement re-review : les proxys sudo sont appelables par call_kw
        # sans ACL de méthode — un compte portail ne doit pas pouvoir
        # énumérer le schéma (modèles/champs) via ces proxys.
        portal = new_test_user(
            self.env, login='dash_portal', groups='base.group_portal')
        Widget = self.env['oski.dashboard.widget'].with_user(portal)
        with self.assertRaises(AccessError):
            Widget.get_available_models()
        model_partner = self.env['ir.model']._get('res.partner')
        with self.assertRaises(AccessError):
            Widget.get_model_fields(model_partner.id)

    def test_widget_domain_check_cold_cache(self):
        # B2 : _check_domain lisait model_id.model sans sudo() — AccessError
        # en prod à cache froid. Le create() ci-dessous se fait juste après
        # invalidate_all() (cache froid simulé), sans lecture superuser
        # préalable pour le réchauffer.
        model_partner = self.env['ir.model']._get('res.partner')
        self.env.invalidate_all()
        widget = self.env['oski.dashboard.widget'].with_user(self.user_a).create({
            'dashboard_id': self.dash_a.id, 'name': 'ColdCache', 'widget_type': 'kpi',
            'model_id': model_partner.id, 'domain': "[('is_company', '=', True)]",
        })
        self.assertTrue(widget)

    def test_toggle_favorite_shared_reader(self):
        # M1 : un lecteur partagé (accès via group_ids, pas propriétaire)
        # doit pouvoir basculer son propre favori — refusé par
        # rule_dashboard_own_write avec un write() direct côté client.
        group = self.env['res.groups'].sudo().create({'name': 'Equipe Fav'})
        self.dash_a.sudo().group_ids = group
        self.user_b.sudo().write({'group_ids': [(4, group.id)]})
        self.dash_a.with_user(self.user_b).action_toggle_favorite()
        self.assertIn(self.user_b, self.dash_a.sudo().favorite_user_ids)
        self.dash_a.with_user(self.user_b).action_toggle_favorite()
        self.assertNotIn(self.user_b, self.dash_a.sudo().favorite_user_ids)

    def test_toggle_favorite_no_access_denied(self):
        user_c = new_test_user(self.env, login='dash_c')
        with self.assertRaises(AccessError):
            self.dash_a.with_user(user_c).action_toggle_favorite()
