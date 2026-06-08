from odoo.tests.common import TransactionCase


class TestLoginBranding(TransactionCase):

    def test_config_params_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "oski_login_bg_color": "#112233",
            "oski_login_accent_color": "#445566",
        })
        settings.execute()
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_param("oski_login.bg_color"), "#112233")
        self.assertEqual(icp.get_param("oski_login.accent_color"), "#445566")

    def test_template_inherits_login_layout(self):
        view = self.env.ref("oski_login_branding.oski_login_branding")
        self.assertEqual(view.inherit_id.key, "web.login_layout")

    def test_company_login_logo_field(self):
        import base64
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n")
        company = self.env.company
        company.oski_login_logo = png
        self.assertTrue(company.oski_login_logo)
