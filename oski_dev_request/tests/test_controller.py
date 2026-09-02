import re

from odoo.tests import HttpCase, tagged

FORM_URL = "/apps/demande-developpement"
SUBMIT_URL = "/apps/demande-developpement/submit"


@tagged("post_install", "-at_install")
class TestDevRequestController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Portail Test",
            "login": "portal_devreq",
            "password": "portal_devreq",
            "email": "portal_devreq@test.com",
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })

    def setUp(self):
        super().setUp()
        # Le formulaire impose un temps de remplissage minimum : un test le
        # franchit en quelques millisecondes, on neutralise le délai.
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_dev_request.min_fill_seconds", "0")

    def _csrf(self):
        """Récupère le token CSRF depuis le formulaire."""
        r = self.url_open(FORM_URL)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        self.assertTrue(m, "csrf_token absent du formulaire")
        return m.group(1)

    def test_form_is_open_to_visitors(self):
        """Ouvert au public depuis la 19.0.2.0.0 : plus de détour par la connexion.

        authenticate(None, None) = session publique liée à la db (évite le
        routeur nodb -> 404 sur les routes website non authentifiées).
        """
        self.authenticate(None, None)
        r = self.url_open(FORM_URL)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("/web/login", r.url)
        self.assertIn("Request a custom module", r.text)

    def test_form_renders_when_logged(self):
        self.authenticate("portal_devreq", "portal_devreq")
        r = self.url_open(FORM_URL)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Request a custom module", r.text)

    def test_submit_creates_request(self):
        self.authenticate("portal_devreq", "portal_devreq")
        token = self._csrf()
        data = {
            "csrf_token": token,
            "requester_name": "Jean Web",
            "email": "jean.web@test.com",
            "subject": "Besoin module facturation",
            "description": "Description du besoin",
            "budget_range": "b_500_1500",
            "delivery_mode": "store",
            "odoo_version": "19.0",
        }
        r = self.url_open(SUBMIT_URL, data=data)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Thank you", r.text)
        rec = self.env["oski.dev.request"].search(
            [("subject", "=", "Besoin module facturation")], limit=1)
        self.assertTrue(rec, "La demande doit être créée")
        self.assertTrue(rec.name.startswith("DR"))

    def test_submit_missing_required(self):
        self.authenticate("portal_devreq", "portal_devreq")
        token = self._csrf()
        data = {
            "csrf_token": token,
            "requester_name": "Sans Objet",
            "email": "x@test.com",
            "subject": "",
            "description": "",
            "budget_range": "to_discuss",
        }
        r = self.url_open(SUBMIT_URL, data=data)
        self.assertIn("required fields", r.text)
        self.assertFalse(self.env["oski.dev.request"].search(
            [("requester_name", "=", "Sans Objet")]))

    def test_submit_bad_extension_rejected(self):
        self.authenticate("portal_devreq", "portal_devreq")
        token = self._csrf()
        data = {
            "csrf_token": token,
            "requester_name": "Fichier Exe",
            "email": "exe@test.com",
            "subject": "Avec exe",
            "description": "desc",
            "budget_range": "to_discuss",
        }
        files = {"attachments": ("malware.exe", b"MZ binary", "application/octet-stream")}
        r = self.url_open(SUBMIT_URL, data=data, files=files)
        self.assertIn("not allowed", r.text)
        self.assertFalse(self.env["oski.dev.request"].search(
            [("subject", "=", "Avec exe")]))

    def test_submit_with_valid_attachment(self):
        self.authenticate("portal_devreq", "portal_devreq")
        token = self._csrf()
        data = {
            "csrf_token": token,
            "requester_name": "Avec PDF",
            "email": "pdf@test.com",
            "subject": "Avec pdf valide",
            "description": "desc",
            "budget_range": "to_discuss",
        }
        files = {"attachments": ("cahier.pdf", b"%PDF-1.4 test", "application/pdf")}
        r = self.url_open(SUBMIT_URL, data=data, files=files)
        self.assertIn("Thank you", r.text)
        rec = self.env["oski.dev.request"].search(
            [("subject", "=", "Avec pdf valide")], limit=1)
        self.assertTrue(rec)
        self.assertEqual(len(rec.attachment_ids), 1)
        self.assertEqual(rec.attachment_ids.name, "cahier.pdf")
