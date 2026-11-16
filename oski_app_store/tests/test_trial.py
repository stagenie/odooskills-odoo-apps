"""Essai 1 h : bouton, formulaire, limites, appel signé, sondage, webhook, courriel.

Le service d'essai (VPS démo) n'est joignable que depuis l'IP du store : il est
simulé ici par `FakeTrialService`, qui vérifie la signature de chaque requête
avec la même règle que le vrai service (API.md § 1).
"""
import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

from odoo import Command, fields
from odoo.tests import tagged
from odoo.http import GeoIP
from odoo.tests.common import HttpCase
from odoo.tools.misc import hmac as odoo_hmac

from odoo.addons.oski_app_store.controllers.trial import FORM_SCOPE, HONEYPOT_FIELD
from odoo.addons.oski_app_store.models import oski_module_trial as trial_mod
from odoo.addons.oski_app_store.models.oski_module_trial import sign, verify_signature

from .common_i18n import activate_french

SECRET = "ab" * 32
LOGIN_URL = "https://trial20.lab.odooskills.com/web/login?db=trial20_x&oski_trial_token=first"


class FakeResponse:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("no json")
        return self._data


class FakeTrialService:
    """Service d'essai simulé : contrôle la signature, rend l'état programmé."""

    def __init__(self):
        self.calls = []
        self.status = "queued"
        self.extra = {"queue_position": 2}
        self.create_response = None   # (statut, corps) pour forcer un refus
        self.create_once = []         # réponses à un seul usage, prises avant create_response
        self.deleted = []
        self.down = False
        self.login_counter = 0

    def trial(self, **extra):
        data = {
            "trial_id": "remote123",
            "store_trial_id": next(
                (c["payload"]["store_trial_id"] for c in self.calls if c["payload"]), "0"),
            "module": "oski_trial_demo",
            "version": "20.0",
            "status": self.status,
            "created_at": "2026-11-14T07:42:19Z",
        }
        data.update(self.extra)
        data.update(extra)
        return data

    def __call__(self, method, url, data=None, headers=None, timeout=None):
        if self.down:
            raise trial_mod.requests.ConnectionError("unreachable")
        path = "/" + url.split("://", 1)[1].split("/", 1)[1]
        body = data or b""
        error = verify_signature(
            SECRET, method, path, body,
            headers.get("X-Oski-Timestamp"), headers.get("X-Oski-Signature"),
        )
        payload = json.loads(body) if body else None
        self.calls.append({"method": method, "path": path, "payload": payload,
                           "headers": headers, "url": url, "sig_error": error})
        if error:
            return FakeResponse(401, {"error": "bad_signature", "message": "x"})
        if method == "POST" and path == "/trial":
            if self.create_once:
                return FakeResponse(*self.create_once.pop(0))
            if self.create_response:
                return FakeResponse(*self.create_response)
            return FakeResponse(202, self.trial())
        if method == "GET":
            return FakeResponse(200, self.trial(trial_id=path.rsplit("/", 1)[1]))
        if method == "DELETE":
            remote_id = path.rsplit("/", 1)[1]
            self.deleted.append(remote_id)
            return FakeResponse(200, self.trial(trial_id=remote_id, status="expired",
                                                expires_at="2026-11-14T08:42:23Z"))
        if method == "POST" and path.endswith("/login"):
            self.login_counter += 1
            if self.status != "ready":
                return FakeResponse(409, {"error": "not_ready", "message": "x"})
            return FakeResponse(200, self.trial(
                login_url=LOGIN_URL.replace("first", "new%s" % self.login_counter)))
        return FakeResponse(404, {"error": "not_found"})


@tagged("post_install", "-at_install")
class TestTrial(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        Param = cls.env["ir.config_parameter"].sudo()
        Param.set_param("oski.trial.enabled", "True")
        Param.set_param("oski.trial.secret", SECRET)
        Param.set_param("oski.trial.api_url", "https://trial.example.test")
        cls.Versions = cls.env["oski.odoo.version"]
        cls.website = cls.env["website"].get_current_website()
        cls.currency = cls.website.company_id.currency_id
        cls.categ = cls.env["product.category"].create({"name": "Modules Odoo (essai)"})
        cls.product = cls.env["product.template"].create({
            "name": "oski_trial_demo", "type": "service", "list_price": 100.0,
            "categ_id": cls.categ.id, "taxes_id": [(6, 0, [])],
            "is_published": True, "sale_ok": True,
        })
        cls.module = cls._make_module("oski_trial_demo", False, ("20.0", "19.0"), cls.product)
        cls.free = cls._make_module("oski_trial_free", True, ("20.0",))

    @classmethod
    def _make_module(cls, name, is_free, versions, product=None):
        module = cls.env["oski.module"].create({
            "name": "Trial demo %s" % name, "technical_name": name,
            "is_free": is_free, "is_published": True, "price": 0 if is_free else 100.0,
            "currency_id": cls.currency.id,
            "product_tmpl_id": product.id if product else False,
        })
        for v in versions:
            attachment = cls.env["ir.attachment"].create({
                "name": "%s-%s.zip" % (name, v), "raw": b"ZIP", "mimetype": "application/zip",
            })
            cls.env["oski.module.version"].create({
                "module_id": module.id,
                "odoo_version_id": cls.Versions.search([("name", "=", v)], limit=1).id,
                "module_version": "%s.1.0.0" % v, "attachment_id": attachment.id,
            })
        return module

    def setUp(self):
        super().setUp()
        self.service = FakeTrialService()
        patcher = patch.object(trial_mod.requests, "request", self.service)
        patcher.start()
        self.addCleanup(patcher.stop)

    # -- outils ---------------------------------------------------------------

    def _form_url(self, module=None, lang=""):
        return "%s/apps/trial/start/%s" % (lang, (module or self.module).id)

    def _stamp(self, age=10):
        ts = str(int(time.time()) - age)
        return ts, odoo_hmac(self.env(su=True), FORM_SCOPE, ts)

    def _submit(self, email="visitor@example.com", version="20.0", terms=True, age=10,
                honeypot="", lang=""):
        page = self.url_open(self._form_url(lang=lang))
        self.assertEqual(page.status_code, 200)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        ts, sig = self._stamp(age)
        data = {"csrf_token": csrf, "form_ts": ts, "form_sig": sig, "email": email,
                "version": version, "country_id": str(self.env.ref("base.fr").id),
                HONEYPOT_FIELD: honeypot}
        if terms:
            data["accept_terms"] = "1"
        return self.url_open(self._form_url(lang=lang), data=data, allow_redirects=False)

    def _trials(self):
        return self.env["oski.module.trial"].search([("module_id", "=", self.module.id)])

    def _webhook(self, payload, secret=SECRET, ts=None, raw_sig=None):
        body = json.dumps(payload).encode()
        ts = int(time.time()) if ts is None else ts
        sig = raw_sig or "sha256=%s" % sign(secret, "POST", "/apps/trial/webhook", body, ts)
        return self.url_open(
            "/apps/trial/webhook", data=body,
            headers={"X-Oski-Timestamp": str(ts), "X-Oski-Signature": sig,
                     "Content-Type": "application/json"},
        ), sig

    def _ready_trial(self, **values):
        vals = {
            "module_id": self.module.id, "odoo_version": "20.0", "lang": "en_US",
            "email": "ready@example.com", "state": "ready", "remote_trial_id": "remote123",
            "ready_at": fields.Datetime.now() - timedelta(minutes=30),
            "expires_at": fields.Datetime.now() + timedelta(minutes=30),
            "buy_url": "https://apps.odooskills.com/apps/oski_trial_demo?v=20.0",
            "partner_id": self.env["res.partner"].create(
                {"name": "ready", "email": values.get("email", "ready@example.com")}).id,
        }
        vals.update(values)
        return self.env["oski.module.trial"].create(vals)

    # -- signature ------------------------------------------------------------

    def test_signature_matches_api_example(self):
        """Vecteur de test d'API.md § 1."""
        self.assertEqual(
            hashlib.sha256(b"{}").hexdigest(),
            "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        )
        self.assertEqual(
            sign("s" * 48, "POST", "/trial", b"{}", 1700000000),
            "6001aa151f29af69ec6306e3dac48d768991c272fc2ee815f7790aa1b90520d6",
        )

    # -- bouton de la fiche -----------------------------------------------------

    def test_button_on_paid_module(self):
        body = self.url_open(self.module.website_url).text
        self.assertIn("Try it free for 1 hour", body)
        self.assertIn("/apps/trial/start/%s?v=20.0" % self.module.id, body)

    def test_button_in_french(self):
        activate_french(self.env)
        body = self.url_open("/fr" + self.module.website_url).text
        self.assertIn("Essayer gratuitement 1 h", body)
        self.assertIn("/fr/apps/trial/start/%s" % self.module.id, body)

    def test_button_absent_on_free_module(self):
        body = self.url_open(self.free.website_url).text
        self.assertNotIn("Try it free for 1 hour", body)
        self.assertEqual(self.url_open(self._form_url(self.free)).status_code, 404)

    def test_button_absent_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param("oski.trial.enabled", "False")
        body = self.url_open(self.module.website_url).text
        self.assertNotIn("Try it free for 1 hour", body)
        self.assertEqual(self.url_open(self._form_url()).status_code, 404)

    def test_form_offers_only_versions_with_archive(self):
        body = self.url_open(self._form_url()).text
        self.assertRegex(body, r'<option value="20.0" selected="[^"]+">Odoo 20</option>')
        self.assertIn('value="19.0"', body)
        self.assertNotIn('value="18.0"', body)
        self.assertIn(HONEYPOT_FIELD, body)
        # Le pays n'est plus demandé : il est déterminé côté serveur.
        self.assertIn('id="oski_trial_version"', body)
        self.assertNotIn("oski_trial_country", body)
        self.assertNotIn('name="country_id"', body)

    # -- création ---------------------------------------------------------------

    def test_create_trial_calls_signed_service(self):
        with patch.object(GeoIP, "country_code", new_callable=PropertyMock, return_value="FR"):
            resp = self._submit()
        self.assertEqual(resp.status_code, 303)
        trial = self._trials()
        self.assertEqual(len(trial), 1)
        self.assertIn("/apps/trial/%s/%s" % (trial.id, trial.sudo().access_token),
                      resp.headers["Location"])
        self.assertEqual(trial.email, "visitor@example.com")
        self.assertEqual(trial.partner_id.email, "visitor@example.com")
        self.assertEqual(trial.country_id, self.env.ref("base.fr"))
        self.assertEqual(trial.country_source, "geoip")
        self.assertEqual(trial.state, "queued")
        self.assertEqual(trial.remote_trial_id, "remote123")
        self.assertEqual(trial.lang, "en_US")
        # Empreinte salée : jamais l'adresse en clair.
        self.assertTrue(trial.ip_hash)
        self.assertNotIn("127.0.0.1", trial.ip_hash)
        self.assertEqual(trial.ip_hash, trial._hash_ip("127.0.0.1"))
        call = self.service.calls[0]
        self.assertIsNone(call["sig_error"])
        self.assertEqual((call["method"], call["path"]), ("POST", "/trial"))
        self.assertEqual(call["payload"]["module"], "oski_trial_demo")
        self.assertEqual(call["payload"]["version"], "20.0")
        self.assertEqual(call["payload"]["store_trial_id"], str(trial.id))
        self.assertEqual(call["payload"]["email"], "visitor@example.com")
        self.assertTrue(call["payload"]["buy_url"].startswith("https://apps.odooskills.com/apps/"))

    def test_posted_country_is_ignored_geoip_wins(self):
        """Un country_id envoyé (ici France, par _submit) est ignoré : GeoIP fait foi."""
        with patch.object(GeoIP, "country_code", new_callable=PropertyMock, return_value="BE"):
            resp = self._submit(email="geo@example.com")
        self.assertEqual(resp.status_code, 303)
        trial = self._trials()
        self.assertEqual(trial.country_id, self.env.ref("base.be"))
        self.assertEqual(trial.country_source, "geoip")
        self.assertEqual(trial.partner_id.country_id, self.env.ref("base.be"))

    def test_posted_country_is_ignored_without_geoip(self):
        """Sans géolocalisation, pays inconnu même si le navigateur en envoie un."""
        with patch.object(GeoIP, "country_code", new_callable=PropertyMock, return_value=None):
            resp = self._submit(email="nogeo@example.com")
        self.assertEqual(resp.status_code, 303)
        trial = self._trials()
        self.assertFalse(trial.country_id)
        self.assertEqual(trial.country_source, "unknown")

    def test_create_trial_in_french_sends_french_lang(self):
        activate_french(self.env)
        resp = self._submit(lang="/fr")
        self.assertEqual(resp.status_code, 303)
        self.assertIn("/fr/apps/trial/", resp.headers["Location"])
        trial = self._trials()
        self.assertEqual(trial.lang, "fr_FR")
        self.assertEqual(self.service.calls[0]["payload"]["lang"], "fr_FR")
        self.assertTrue(self.service.calls[0]["payload"]["buy_url"].startswith(
            "https://apps.odooskills.com/fr/apps/"))

    def test_robots_rejected(self):
        self.assertEqual(self._submit(honeypot="http://spam.example").status_code, 400)
        self.assertEqual(self._submit(age=0).status_code, 400)   # envoyé trop vite
        self.assertFalse(self._trials())
        self.assertFalse(self.service.calls)

    def test_email_and_terms_required(self):
        self.assertEqual(self._submit(email="").status_code, 400)
        self.assertEqual(self._submit(email="not-an-email").status_code, 400)
        resp = self._submit(terms=False)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Please accept the terms of use.", resp.text)
        self.assertFalse(self._trials())

    # -- limites ------------------------------------------------------------------

    def test_one_active_trial_per_email(self):
        self._ready_trial(email="visitor@example.com")
        resp = self._submit(email="Visitor@Example.com")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("A trial is already running for this e-mail address.", resp.text)
        self.assertFalse(self.service.calls)

    def test_expired_trial_allows_new_one(self):
        self._ready_trial(email="visitor@example.com", state="expired")
        self.assertEqual(self._submit().status_code, 303)

    def test_three_trials_per_ip_per_day(self):
        Trial = self.env["oski.module.trial"]
        ip_hash = Trial._hash_ip("127.0.0.1")
        for i in range(3):
            self._ready_trial(email="ip%s@example.com" % i, state="expired", ip_hash=ip_hash)
        resp = self._submit(email="fourth@example.com")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many trials from your connection", resp.text)
        self.assertFalse(self.service.calls)

    def test_service_refusal_is_explained(self):
        self.service.create_response = (409, {"error": "already_active", "message": "x"})
        resp = self._submit()
        trial = self._trials()
        self.assertEqual((trial.state, trial.error_code), ("error", "already_active"))
        page = self.url_open(resp.headers["Location"]).text
        self.assertIn("A trial is already running for this e-mail address.", page)

    def test_service_unreachable_is_explained(self):
        self.service.down = True
        resp = self._submit()
        trial = self._trials()
        self.assertEqual((trial.state, trial.error_code), ("error", "unavailable"))
        page = self.url_open(resp.headers["Location"]).text
        self.assertIn("The trial service is not available right now.", page)
        self.assertIn("Try again", page)

    # -- sondage et ouverture -------------------------------------------------------

    def test_poll_until_ready_then_open(self):
        resp = self._submit()
        trial = self._trials()
        wait_url = resp.headers["Location"]
        page = self.url_open(wait_url).text
        self.assertIn("2 person(s) ahead of you", page)
        self.assertIn('data-status-url="', page)
        status = self.url_open(wait_url + "/status").json()
        self.assertEqual(status["state"], "queued")
        self.assertTrue(status["pending"])
        self.assertFalse(status["open_url"])

        self.service.status, self.service.extra = "building", {"phase": "template"}
        status = self.url_open(wait_url + "/status").json()
        self.assertEqual(status["state"], "building")
        self.assertIn("1 to 5 minutes", status["message"])

        self.service.status = "ready"
        self.service.extra = {"login_url": LOGIN_URL, "expires_at": "2026-11-14T08:42:23Z",
                              "remaining_seconds": 3589}
        status = self.url_open(wait_url + "/status").json()
        self.assertEqual(status["state"], "ready")
        self.assertTrue(status["open_url"].endswith("/open"))
        self.assertEqual(trial.expires_at, datetime(2026, 11, 14, 8, 42, 23))
        # Chaque sondage est signé à nouveau (anti-rejeu du service).
        sigs = [c["headers"]["X-Oski-Signature"] for c in self.service.calls]
        self.assertTrue(all(c["sig_error"] is None for c in self.service.calls))
        self.assertEqual([c["method"] for c in self.service.calls], ["POST", "GET", "GET", "GET", "GET"])
        self.assertEqual(len(sigs), len(self.service.calls))

        first = self.url_open(status["open_url"], allow_redirects=False)
        self.assertEqual(first.status_code, 303)
        self.assertEqual(first.headers["Location"], LOGIN_URL)
        # Lien à usage unique : rouvrir demande un nouveau jeton au service.
        again = self.url_open(status["open_url"], allow_redirects=False)
        self.assertEqual(again.headers["Location"], LOGIN_URL.replace("first", "new1"))
        self.assertEqual(self.service.calls[-1]["path"], "/trial/remote123/login")

    def test_wait_page_requires_token(self):
        self._submit()
        trial = self._trials()
        self.assertEqual(self.url_open("/apps/trial/%s/wrong" % trial.id).status_code, 404)
        self.assertEqual(
            self.url_open("/apps/trial/%s/wrong/status" % trial.id).status_code, 404)

    def test_wait_page_in_french(self):
        activate_french(self.env)
        resp = self._submit(lang="/fr")
        page = self.url_open(resp.headers["Location"]).text
        self.assertIn("2 personne(s) avant vous", page)
        status = self.url_open(resp.headers["Location"] + "/status").json()
        self.assertIn("personne(s) avant vous", status["message"])

    # -- webhook et courriel --------------------------------------------------------------

    def _payload(self, trial, event="trial.expired"):
        return {
            "event": event, "trial_id": "remote123", "store_trial_id": str(trial.id),
            "module": "oski_trial_demo", "version": "20.0",
            "status": "expired" if event == "trial.expired" else "failed",
            "ready_at": "2026-11-14T07:42:23Z", "ended_at": "2026-11-14T08:45:02Z",
            "error": None if event == "trial.expired" else "build_failed",
        }

    def _end_mails(self, trial):
        return self.env["mail.mail"].sudo().search(
            [("model", "=", "oski.module.trial"), ("res_id", "=", trial.id)])

    def test_webhook_expires_trial_and_mails_once(self):
        trial = self._ready_trial()
        resp, sig = self._webhook(self._payload(trial))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(trial.state, "expired")
        self.assertEqual(trial.ended_at, datetime(2026, 11, 14, 8, 45, 2))
        mails = self._end_mails(trial)
        self.assertEqual(len(mails), 1)
        self.assertIn("Your trial of", mails.subject)
        self.assertIn("has ended", mails.subject)
        self.assertIn(trial.buy_url, mails.body_html)
        self.assertNotIn("oski_trial_token", mails.body_html)
        # Le service réémet (réponse perdue) : nouvelle signature, aucun 2e courriel.
        resp2, _sig = self._webhook(self._payload(trial), ts=int(time.time()) - 1)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(len(self._end_mails(trial)), 1)
        # Rejeu exact de la même requête : refusé.
        replay, _sig = self._webhook(self._payload(trial), raw_sig=sig)
        self.assertEqual(replay.status_code, 401)

    def test_webhook_short_lang_code(self):
        """Essai enregistré en « en » (1er essai réel du 14/11 : webhook 422)."""
        trial = self._ready_trial(lang="en", email="short-lang@example.com")
        self.assertEqual(trial.lang, "en_US")
        trial.write({"lang": "fr"})
        self.assertEqual(trial.lang, "fr_FR" if self.env["res.lang"]._lang_get("fr_FR") else "en_US")
        trial.write({"lang": "xx"})
        self.assertEqual(trial.lang, "en_US")
        resp, _sig = self._webhook(self._payload(trial))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(trial.state, "expired")
        self.assertEqual(len(self._end_mails(trial)), 1)

    def test_webhook_bad_signature_refused(self):
        trial = self._ready_trial()
        resp, _sig = self._webhook(self._payload(trial), secret="wrong" * 10)
        self.assertEqual(resp.status_code, 401)
        stale, _sig = self._webhook(self._payload(trial), ts=int(time.time()) - 900)
        self.assertEqual(stale.status_code, 401)
        self.assertEqual(stale.json()["error"], "stale_request")
        self.assertEqual(trial.state, "ready")
        self.assertFalse(self._end_mails(trial))

    def test_webhook_failed_no_mail(self):
        trial = self._ready_trial(state="building", ready_at=False)
        resp, _sig = self._webhook(self._payload(trial, "trial.failed"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual((trial.state, trial.error_code), ("failed", "build_failed"))
        self.assertFalse(self._end_mails(trial))

    def test_webhook_unknown_trial(self):
        trial = self._ready_trial()
        payload = self._payload(trial)
        payload["store_trial_id"] = "999999"
        resp, _sig = self._webhook(payload)
        self.assertEqual(resp.status_code, 404)

    def test_end_mail_in_french_with_launch_price(self):
        activate_french(self.env)
        group = self.env.ref("product.group_product_pricelist")
        self.env.ref("base.group_user").write({"implied_ids": [Command.link(group.id)]})
        self.env["product.pricelist"].search([]).action_archive()
        self.env["product.pricelist"].create({
            "name": "Launch 2026", "currency_id": self.currency.id,
            "website_id": self.website.id, "selectable": False, "sequence": 1,
            "item_ids": [Command.create({
                "applied_on": "2_product_category", "categ_id": self.categ.id,
                "compute_price": "percentage", "percent_price": 30.0,
                "date_end": datetime(2099, 12, 31, 23, 59, 59),
            })],
        })
        trial = self._ready_trial(lang="fr_FR")
        resp, _sig = self._webhook(self._payload(trial))
        self.assertEqual(resp.status_code, 200)
        mail = self._end_mails(trial)
        self.assertEqual(len(mail), 1)
        self.assertIn("Votre essai de", mail.subject)
        self.assertIn("est terminé", mail.subject)
        self.assertIn("Acheter le module", mail.body_html)
        self.assertIn("30", mail.body_html)
        self.assertIn("31 décembre 2099", mail.body_html)

    def test_end_mail_english_launch_price(self):
        self.env["product.pricelist"].search([]).action_archive()
        self.env["product.pricelist"].create({
            "name": "Launch 2026", "currency_id": self.currency.id,
            "website_id": self.website.id, "selectable": False, "sequence": 1,
            "item_ids": [Command.create({
                "applied_on": "2_product_category", "categ_id": self.categ.id,
                "compute_price": "percentage", "percent_price": 30.0,
                "date_end": datetime(2099, 12, 31, 23, 59, 59),
            })],
        })
        trial = self._ready_trial()
        self.assertIn("Launch price:", trial.pricing_note)
        self.assertIn("(30% off) until December 31, 2099", trial.pricing_note)

    # -- ré-essai après la fin d'un essai ---------------------------------------------

    def _age(self, trial, **delta):
        """Vieillit un essai (create_date n'est pas écrivable par l'ORM)."""
        self.env.cr.execute(
            "UPDATE oski_module_trial SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(**delta), trial.id))
        trial.invalidate_recordset(["create_date"])

    def _posts(self):
        return [c for c in self.service.calls if c["method"] == "POST" and c["path"] == "/trial"]

    def test_new_trial_after_webhook_expiry(self):
        """Même e-mail, même module, même version : accepté une fois l'essai terminé."""
        first_resp = self._submit()
        first = self._trials()
        self.assertEqual(first.state, "queued")
        resp, _sig = self._webhook(self._payload(first))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(first.state, "expired")
        second_resp = self._submit()
        self.assertEqual(second_resp.status_code, 303)
        self.assertNotEqual(second_resp.headers["Location"], first_resp.headers["Location"])
        self.assertEqual(len(self._trials()), 2)
        self.assertEqual(len(self._posts()), 2)

    def test_hour_elapsed_before_purge_ends_old_trial(self):
        """Heure écoulée, base pas encore purgée (≤ 5 min) : DELETE puis nouvel essai."""
        old = self._ready_trial(email="visitor@example.com", remote_trial_id="oldremote",
                                expires_at=fields.Datetime.now() - timedelta(minutes=2))
        resp = self._submit()
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(self.service.deleted, ["oldremote"])
        self.assertEqual(old.state, "expired")
        self.assertTrue(old.ended_at)
        self.assertEqual(len(self._posts()), 1)
        # Le webhook de la purge arrive ensuite : courriel de fin envoyé une fois.
        self._webhook(dict(self._payload(old), trial_id="oldremote"))
        self.assertEqual(len(self._end_mails(old)), 1)

    def test_service_409_on_finished_trial_retries_once(self):
        """Le service cite un essai fini que le store croyait en cours : terminé, redemandé."""
        old = self._ready_trial(email="other-state@example.com", remote_trial_id="oldremote",
                                state="building", expires_at=False)
        self._age(old, hours=7)
        self.service.create_once = [
            (409, {"error": "already_active", "message": "x", "trial_id": "oldremote"})]
        self.service.status = "queued"
        resp = self._submit()
        self.assertEqual(resp.status_code, 303)
        new = self._trials() - old
        self.assertEqual(new.state, "queued")
        self.assertEqual(self.service.deleted, ["oldremote"])
        self.assertEqual(len(self._posts()), 2)

    def test_running_trial_refused_with_time_left(self):
        self._ready_trial(email="visitor@example.com",
                          expires_at=fields.Datetime.now() + timedelta(minutes=30))
        resp = self._submit()
        self.assertEqual(resp.status_code, 429)
        self.assertRegex(resp.text, r"it ends in about (29|30) min, then you can start a new one")
        self.assertNotIn("Return to my current trial", resp.text)
        self.assertFalse(self.service.calls)

    def test_running_trial_link_only_for_its_browser(self):
        first_resp = self._submit()
        wait_url = first_resp.headers["Location"]
        again = self._submit()
        self.assertEqual(again.status_code, 429)
        self.assertIn("Return to my current trial", again.text)
        self.assertIn('href="%s"' % wait_url, again.text)
        self.assertEqual(len(self._posts()), 1)
        # Autre navigateur (pas de session) : refus sans lien vers la base d'un autre.
        self.opener.cookies.clear()
        other = self._submit()
        self.assertEqual(other.status_code, 429)
        self.assertIn("as soon as it ends (1 hour at most)", other.text)
        self.assertNotIn("Return to my current trial", other.text)
        self.assertNotIn(wait_url, other.text)

    def test_stale_pending_trial_does_not_block(self):
        """Webhook perdu : un essai resté « en file » depuis 7 h ne bloque plus l'e-mail."""
        old = self._ready_trial(email="visitor@example.com", state="queued", expires_at=False)
        self._age(old, hours=7)
        self.assertEqual(self._submit().status_code, 303)

    def test_email_limit_per_day(self):
        for _i in range(3):
            self._ready_trial(email="visitor@example.com", state="expired")
        resp = self._submit()
        self.assertEqual(resp.status_code, 429)
        self.assertIn("You have used the 3 trials allowed per e-mail address in 24 hours.", resp.text)
        self.assertRegex(resp.text, r"You can start a new one in about (23|24) hour\(s\)")
        self.assertFalse(self.service.calls)
        # Paramètre système : la limite se règle sans code.
        self.env["ir.config_parameter"].sudo().set_param("oski.trial.max_per_email_per_day", "4")
        self.assertEqual(self._submit().status_code, 303)

    def test_email_limit_counts_last_24_hours_only(self):
        for _i in range(3):
            self._age(self._ready_trial(email="visitor@example.com", state="expired"), hours=25)
        self.assertEqual(self._submit().status_code, 303)

    def test_email_limit_waits_for_oldest_trial(self):
        trials = [self._ready_trial(email="visitor@example.com", state="expired") for _i in range(3)]
        self._age(trials[0], hours=22, minutes=30)
        resp = self._submit()
        self.assertRegex(resp.text, r"in about 2 hour\(s\)")

    def test_refused_and_failed_trials_do_not_count(self):
        self._ready_trial(email="visitor@example.com", state="error", error_code="unavailable")
        self._ready_trial(email="visitor@example.com", state="error", error_code="queue_full")
        self._ready_trial(email="visitor@example.com", state="failed", error_code="build_failed")
        self._ready_trial(email="visitor@example.com", state="expired")
        self.assertEqual(self._submit().status_code, 303)

    def test_bad_limit_parameter_falls_back_to_default(self):
        Param = self.env["ir.config_parameter"].sudo()
        for value in ("0", "-1", "abc"):
            Param.set_param("oski.trial.max_per_email_per_day", value)
            self.assertEqual(self.env["oski.module.trial"]._limit_param(
                "oski.trial.max_per_email_per_day", 3), 3)

    def test_expired_wait_page_offers_new_trial(self):
        resp = self._submit()
        trial = self._trials()
        self._webhook(self._payload(trial))
        page = self.url_open(resp.headers["Location"]).text
        self.assertIn("This trial has ended.", page)
        self.assertIn("Start a new trial", page)
        self.assertIn("/apps/trial/start/%s?v=20.0" % self.module.id, page)

    def test_retry_messages_in_french(self):
        activate_french(self.env)
        running = self._ready_trial(email="visitor@example.com",
                                    expires_at=fields.Datetime.now() + timedelta(minutes=30))
        resp = self._submit(lang="/fr")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Un essai est déjà en cours pour cette adresse e-mail.", resp.text)
        self.assertRegex(resp.text, r"il se termine dans environ (29|30) min")
        running.state = "expired"
        for _i in range(2):
            self._ready_trial(email="visitor@example.com", state="expired")
        resp = self._submit(lang="/fr")
        self.assertIn("Vous avez utilisé les 3 essais autorisés par adresse e-mail sur 24 heures.",
                      resp.text)
        self.assertRegex(resp.text, r"Vous pourrez en lancer un nouveau dans environ (23|24) heure\(s\)")
        self.env["ir.config_parameter"].sudo().set_param("oski.trial.max_per_email_per_day", "5")
        first = self._submit(lang="/fr")
        again = self._submit(lang="/fr")
        self.assertIn("Revenir à mon essai en cours", again.text)
        trial = self._trials().filtered(lambda t: t.state == "queued")
        self._webhook(self._payload(trial))
        page = self.url_open(first.headers["Location"]).text
        self.assertIn("Lancer un nouvel essai", page)
