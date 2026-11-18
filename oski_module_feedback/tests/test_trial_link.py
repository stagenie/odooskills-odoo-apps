"""Essai 1 h : lien « Request a change » dans le courriel de fin et la page
d'essai ; le jeton d'essai rattache la demande sans rien ouvrir à autrui."""
import re
from datetime import timedelta
from urllib.parse import unquote

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from ..hooks import MARKER, post_init_hook, uninstall_hook
from .common import make_store_data


@tagged("post_install", "-at_install")
class TestTrialLink(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        make_store_data(cls)
        cls.template = cls.env.ref("oski_app_store.mail_template_trial_ended")

    def _trial(self, email="awa@example.com", state="expired"):
        return self.env["oski.module.trial"].create({
            "module_id": self.paid.id, "odoo_version": "19.0", "lang": "en_US",
            "email": email, "state": state,
            "ready_at": fields.Datetime.now() - timedelta(minutes=70),
            "expires_at": fields.Datetime.now() - timedelta(minutes=10),
        })

    def _raw_body(self):
        self.env.flush_all()
        self.env.cr.execute("SELECT body_html FROM mail_template WHERE id = %s", (self.template.id,))
        return self.env.cr.fetchone()[0]

    # --- courriel de fin d'essai --------------------------------------------

    def test_hook_adds_link(self):
        body = self._raw_body()
        for lang in body:
            self.assertIn(MARKER, body[lang])
            self.assertIn("_feedback_url()", body[lang])
        self.assertIn("Buy the module", body["en_US"])

    def test_hook_idempotent(self):
        post_init_hook(self.env)
        body = self._raw_body()
        self.assertEqual(body["en_US"].count(MARKER), 1)

    def test_uninstall_restores(self):
        uninstall_hook(self.env)
        body = self._raw_body()
        self.assertNotIn(MARKER, body["en_US"])
        self.assertIn("Buy the module", body["en_US"])
        post_init_hook(self.env)
        self.assertIn(MARKER, self._raw_body()["en_US"])

    def test_end_mail_renders_link(self):
        trial = self._trial()
        self.template.invalidate_recordset(["body_html"])
        body = self.template._render_field("body_html", trial.ids)[trial.id]
        self.assertIn(trial._feedback_url().replace("&", "&amp;"), body)
        self.assertIn("source=trial", trial._feedback_url())

    # --- page d'essai ---------------------------------------------------------

    def test_wait_page_link(self):
        self.authenticate(None, None)
        for state in ("ready", "expired"):
            trial = self._trial(state=state)
            page = self.url_open("/apps/trial/%s/%s" % (trial.id, trial.access_token)).text
            self.assertIn("/feedback?source=trial", page, state)

    # --- jeton d'essai sur le formulaire --------------------------------------

    def _post_with_trial(self, token):
        self.authenticate("awa_fb", "awa_fb_12345")
        url = "/apps/m/%s/feedback" % self.paid.technical_name
        resp = self.url_open(url + "?source=trial&trial=" + token)
        csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.text).group(1)
        self.opener.post(self.base_url() + url + "/submit", timeout=30, allow_redirects=False, data={
            "csrf_token": csrf, "request_type": "improvement", "title": "From trial",
            "description": "Seen during the trial.", "source": "trial", "trial": token,
        })
        return self.env["oski.module.feedback"].sudo().search([("title", "=", "From trial")])

    def test_trial_token_ok(self):
        trial = self._trial()
        rec = self._post_with_trial("%s-%s" % (trial.id, trial.access_token))
        self.assertEqual(rec.source, "trial")
        self.assertEqual(rec.trial_id, trial)

    def test_trial_preselects_version(self):
        self.authenticate("awa_fb", "awa_fb_12345")
        trial = self._trial()
        page = self.url_open("/apps/m/%s/feedback?source=trial&trial=%s-%s" % (
            self.paid.technical_name, trial.id, trial.access_token)).text
        self.assertRegex(page, r'<option value="%s"\s+selected' % self.v19.id)

    def test_trial_token_foreign_ignored(self):
        foreign = self._trial(email="someone@else.com")
        rec = self._post_with_trial("%s-%s" % (foreign.id, foreign.access_token))
        self.assertEqual(rec.source, "module_page")
        self.assertFalse(rec.trial_id)
        trial = self._trial()
        rec2 = self._post_with_trial("%s-%s" % (trial.id, "wrongtoken"))
        self.assertFalse(rec2.filtered("trial_id"))

    def test_trial_anonymous_prefill(self):
        self.authenticate(None, None)
        url = "/apps/m/%s/feedback" % self.paid.technical_name
        newcomer = self._trial(email="newcomer@example.com")
        resp = self.url_open("%s?source=trial&trial=%s-%s" % (url, newcomer.id, newcomer.access_token),
                             allow_redirects=False)
        location = unquote(resp.headers["Location"])
        self.assertIn("/web/signup", location)
        self.assertIn("login=newcomer@example.com", location)
        self.assertIn(url, location)
        self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Known", "login": "known@example.com", "password": "known_12345",
            "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])]})
        known = self._trial(email="known@example.com")
        resp = self.url_open("%s?source=trial&trial=%s-%s" % (url, known.id, known.access_token),
                             allow_redirects=False)
        location = unquote(resp.headers["Location"])
        self.assertIn("/web/login", location)
        self.assertIn("login=known@example.com", location)
