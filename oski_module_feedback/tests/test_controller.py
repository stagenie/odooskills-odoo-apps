"""Formulaire « Request a change » : connexion exigée, modules payants
seulement, contrôles serveur."""
import re
from urllib.parse import unquote

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .common import feedback_vals, make_store_data

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@tagged("post_install", "-at_install")
class TestFeedbackForm(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        make_store_data(cls)
        cls.form_url = "/apps/m/%s/feedback" % cls.paid.technical_name
        cls.submit_url = cls.form_url + "/submit"

    def _login(self):
        self.authenticate("awa_fb", "awa_fb_12345")

    def _csrf(self, url=None):
        resp = self.url_open(url or self.form_url)
        self.assertEqual(resp.status_code, 200)
        return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.text).group(1)

    def _payload(self, csrf, **kw):
        vals = {
            "csrf_token": csrf, "request_type": "bug", "title": "Late fee missing",
            "description": "The late fee is not added.", "steps": "1. Return late",
            "odoo_version_id": str(self.v19.id),
        }
        vals.update(kw)
        return vals

    def _post(self, data, files=None):
        return self.opener.post(self.base_url() + self.submit_url, data=data, files=files,
                                timeout=30, allow_redirects=False)

    def _count(self):
        return self.env["oski.module.feedback"].sudo().search_count(
            [("partner_id", "=", self.portal_user.partner_id.id)])

    # --- accès ---------------------------------------------------------------

    def test_anonymous_redirect(self):
        self.authenticate(None, None)
        resp = self.url_open(self.form_url, allow_redirects=False)
        self.assertEqual(resp.status_code, 303)
        location = unquote(resp.headers["Location"])
        self.assertIn("/web/login", location)
        self.assertIn(self.form_url, location)

    def test_anonymous_redirect_keeps_lang(self):
        fr = self.env["res.lang"]._activate_lang("fr_FR")
        en = self.env.ref("base.lang_en")
        # Comme la prod : anglais par défaut, français sous /fr.
        self.env["website"].get_current_website().write({
            "language_ids": [(4, fr.id), (4, en.id)], "default_lang_id": en.id})
        self.env.registry.clear_cache()
        self.authenticate(None, None)
        resp = self.url_open("/fr" + self.form_url, allow_redirects=False)
        self.assertEqual(resp.status_code, 303)
        self.assertIn("/fr/apps/m/", unquote(resp.headers["Location"]))

    def test_free_module_404(self):
        self._login()
        resp = self.url_open("/apps/m/%s/feedback" % self.free.technical_name)
        self.assertEqual(resp.status_code, 404)

    def test_unpublished_404(self):
        self.paid.is_published = False
        self._login()
        self.assertEqual(self.url_open(self.form_url).status_code, 404)

    def test_anonymous_post_refused(self):
        self.authenticate(None, None)
        self._post({"title": "x"})
        self.assertEqual(self._count(), 0)

    # --- formulaire ----------------------------------------------------------

    def test_form_renders(self):
        self._login()
        resp = self.url_open(self.form_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Paid Demo", resp.text)
        for value in ("bug", "change", "improvement", "other"):
            self.assertIn('value="%s"' % value, resp.text)

    def test_submit_creates(self):
        self._login()
        resp = self._post(self._payload(self._csrf()))
        self.assertEqual(resp.status_code, 303)
        rec = self.env["oski.module.feedback"].sudo().search(
            [("partner_id", "=", self.portal_user.partner_id.id)])
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec.source, "module_page")
        self.assertEqual(rec.module_id, self.paid)
        self.assertEqual(rec.request_type, "bug")
        thanks = self.url_open(resp.headers["Location"])
        self.assertIn(rec.name, thanks.text)

    def test_submit_with_attachment(self):
        self._login()
        self._post(self._payload(self._csrf()),
                   files={"attachments": ("screen.png", PNG, "image/png")})
        rec = self.env["oski.module.feedback"].sudo().search(
            [("partner_id", "=", self.portal_user.partner_id.id)])
        self.assertEqual(rec.attachment_ids.mapped("name"), ["screen.png"])
        self.assertEqual(rec.attachment_ids.res_model, "oski.module.feedback")

    def test_submit_missing_title(self):
        self._login()
        resp = self._post(self._payload(self._csrf(), title="  "))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("alert-danger", resp.text)
        self.assertEqual(self._count(), 0)

    def test_attachment_too_big(self):
        self._login()
        big = b"0" * (5 * 1024 * 1024 + 1)
        resp = self._post(self._payload(self._csrf()),
                          files={"attachments": ("big.png", big, "image/png")})
        self.assertIn("alert-danger", resp.text)
        self.assertEqual(self._count(), 0)

    def test_attachment_bad_type(self):
        self._login()
        resp = self._post(self._payload(self._csrf()),
                          files={"attachments": ("tool.exe", b"MZ", "application/octet-stream")})
        self.assertIn("alert-danger", resp.text)
        self.assertEqual(self._count(), 0)

    def test_too_many_attachments(self):
        self._login()
        files = [("attachments", ("s%s.png" % i, PNG, "image/png")) for i in range(4)]
        resp = self._post(self._payload(self._csrf()), files=files)
        self.assertIn("alert-danger", resp.text)
        self.assertEqual(self._count(), 0)

    def test_limit_per_day(self):
        Feedback = self.env["oski.module.feedback"].sudo()
        for _i in range(5):
            Feedback.create(feedback_vals(self))
        self._login()
        resp = self._post(self._payload(self._csrf()))
        self.assertIn("alert-danger", resp.text)
        self.assertEqual(self._count(), 5)

    def test_button_on_paid_page(self):
        self.authenticate(None, None)
        paid_page = self.url_open(self.paid.website_url).text
        free_page = self.url_open(self.free.website_url).text
        self.assertIn(self.form_url, paid_page)
        self.assertNotIn("/feedback", free_page)
