import base64

from odoo.tools.binary import BinaryBytes

from odoo.tests.common import HttpCase, TransactionCase, tagged

# PNG 1 x 1 complet (un en-tête seul n'est pas une image).
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class TestLoginBranding(TransactionCase):

    def test_config_params_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "oski_login_bg_color": "#112233",
            "oski_login_accent_color": "#445566",
        })
        settings.execute()
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_str("oski_login.bg_color"), "#112233")
        self.assertEqual(icp.get_str("oski_login.accent_color"), "#445566")

    def test_template_inherits_login_layout(self):
        view = self.env.ref("oski_login_branding.oski_login_branding")
        self.assertEqual(view.inherit_id.key, "web.login_layout")

    def test_company_login_logo_field(self):
        company = self.env.company
        company.oski_login_logo = BinaryBytes(PNG_1PX)
        self.assertEqual(company.oski_login_logo.content, PNG_1PX)


@tagged("post_install", "-at_install")
class TestLoginPageRendering(HttpCase):
    """La page /web/login doit réellement porter les couleurs et le logo."""

    def test_login_page_shows_branding(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_str("oski_login.bg_color", "#112233")
        icp.set_str("oski_login.accent_color", "#445566")
        company = self.env["res.company"].search([], limit=1)
        company.oski_login_logo = BinaryBytes(PNG_1PX)
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        page = response.text
        self.assertIn("background-color: #112233", page)
        self.assertIn("background-color: #445566", page)
        # Le logo lui-même, pas seulement le préfixe : prouve le rendu du bloc,
        # que 20.0 masque quand la société garde le logo par défaut.
        self.assertIn("data:image;base64,%s" % base64.b64encode(PNG_1PX).decode(), page)

    def test_login_page_untouched_without_settings(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("data:image;base64,", response.text)
        # Sans logo de connexion, le module laisse le comportement du cœur 20.0 :
        # bloc du logo société masqué tant que la société garde le logo par défaut.
        company = self.env["res.company"].search([], limit=1)
        self.assertEqual(
            "/web/binary/company_logo" in response.text,
            not company.uses_default_logo,
        )
