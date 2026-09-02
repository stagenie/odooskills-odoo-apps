"""Le formulaire de demande est ouvert à tous, et tient debout face aux robots."""
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase

FORM_URL = "/apps/demande-developpement"
SUBMIT_URL = "/apps/demande-developpement/submit"


@tagged("post_install", "-at_install")
class TestPublicDevRequestForm(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    # --- utilitaires --------------------------------------------------------

    def _open_form(self):
        """Affiche le formulaire et rend son jeton CSRF (la session suit)."""
        resp = self.url_open(FORM_URL)
        self.assertEqual(resp.status_code, 200)
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.text)
        self.assertTrue(token, "jeton CSRF absent du formulaire")
        return token.group(1)

    def _payload(self, csrf, **kw):
        vals = {
            "csrf_token": csrf,
            "requester_name": "Awa Diop",
            "company_name": "Atelier Nord",
            "email": "awa@example.com",
            "subject": "Suivi des tournées",
            "description": "Planifier les tournées et relever les compteurs.",
            "budget_range": self.env["oski.dev.request"]._fields[
                "budget_range"].selection[0][0],
        }
        vals.update(kw)
        return vals

    def _post(self, payload):
        return self.opener.post(self.base_url() + SUBMIT_URL, data=payload,
                                timeout=30, allow_redirects=False)

    def _count(self):
        return self.env["oski.dev.request"].sudo().search_count([])

    def _no_delay(self):
        """Neutralise le délai minimum, que les tests ne peuvent pas attendre."""
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_dev_request.min_fill_seconds", "0")

    # --- ouverture au public ------------------------------------------------

    def test_form_is_public(self):
        """Un visiteur non connecté atteint le formulaire, sans détour."""
        resp = self.url_open(FORM_URL, allow_redirects=False)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Request a custom module", resp.text)

    def test_form_french_under_fr_prefix(self):
        from odoo.addons.oski_app_store.tests.common_i18n import activate_french
        activate_french(self.env, modules=("oski_app_store", "oski_dev_request"))
        self.assertIn("Request a custom module", self.url_open(FORM_URL).text)
        self.assertIn("Demander un module sur-mesure", self.url_open("/fr" + FORM_URL).text)

    def test_honeypot_is_served_hidden(self):
        body = self.url_open(FORM_URL).text
        self.assertIn('name="website"', body)
        self.assertIn("aria-hidden", body)

    def test_public_submission_creates_a_request(self):
        self._no_delay()
        csrf = self._open_form()
        before = self._count()
        self._post(self._payload(csrf))
        self.assertEqual(self._count(), before + 1)
        req = self.env["oski.dev.request"].sudo().search([], order="id desc", limit=1)
        self.assertEqual(req.email, "awa@example.com")
        self.assertFalse(req.user_id, "un visiteur public ne doit être rattaché à personne")

    # --- garde-fous ---------------------------------------------------------

    def test_honeypot_submission_creates_nothing(self):
        """Le robot repart avec la page de remerciement, et rien en base."""
        self._no_delay()
        csrf = self._open_form()
        before = self._count()
        resp = self._post(self._payload(csrf, website="http://spam.example.com"))
        self.assertIn(resp.status_code, (302, 303))
        self.assertEqual(self._count(), before)

    def test_submission_too_fast_is_refused(self):
        """Trois secondes de remplissage minimum : le délai par défaut s'applique."""
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_dev_request.min_fill_seconds", "3")
        csrf = self._open_form()
        before = self._count()
        resp = self._post(self._payload(csrf))
        self.assertEqual(self._count(), before)
        self.assertIn("too fast", resp.text)

    def test_submission_without_opening_the_form_is_refused(self):
        """Poster sans jamais avoir affiché la page : aucune demande."""
        self._no_delay()
        csrf = self._open_form()
        self.url_open("/web/session/logout")   # la session, donc l'horodatage, tombe
        before = self._count()
        self._post(self._payload(csrf))
        self.assertEqual(self._count(), before)

    def test_rate_limit_stops_the_fourth_submission(self):
        self._no_delay()
        for i in range(3):
            csrf = self._open_form()
            self._post(self._payload(csrf, subject="Besoin %s" % i))
        before = self._count()
        csrf = self._open_form()
        resp = self._post(self._payload(csrf, subject="Un de trop"))
        self.assertEqual(self._count(), before, "la quatrième demande est passée")
        self.assertIn("apps@odooskills.com", resp.text)
