"""Essai 1 h des modules payants : formulaire, page d'attente, webhook.

Le navigateur ne parle jamais au service d'essai : il sonde une route du store,
qui signe chaque requête côté serveur (le secret ne quitte pas le serveur).
"""
import hmac as py_hmac
import json
import logging
import time

from odoo import http
from odoo.http import request
from odoo.tools.misc import hmac as odoo_hmac

from odoo.addons.oski_app_store.controllers.main import OskiAppStore
from odoo.addons.oski_app_store.models.oski_module_trial import (
    DEFAULT_STORE_URL,
    DEFAULT_TRIAL_VERSION,
    PARAM_STORE_URL,
    verify_signature,
)

_logger = logging.getLogger(__name__)

FORM_SCOPE = "oski_app_store.trial_form"
# Un humain met plus de trois secondes à remplir le formulaire ; un robot non.
MIN_FORM_SECONDS = 3
MAX_FORM_SECONDS = 2 * 3600
HONEYPOT_FIELD = "company_website"
WEBHOOK_PATH = "/apps/trial/webhook"


class OskiAppStoreTrial(OskiAppStore):

    # ------------------------------------------------------------------
    # Outils
    # ------------------------------------------------------------------

    def _trial_module(self, module_id):
        module = request.env["oski.module"].sudo().browse(module_id).exists()
        if not module or not module.is_published or module.is_free:
            return None
        return module

    def _form_stamp(self):
        ts = str(int(time.time()))
        return ts, odoo_hmac(request.env(su=True), FORM_SCOPE, ts)

    def _form_stamp_ok(self, ts, sig):
        if not ts or not sig:
            return False
        expected = odoo_hmac(request.env(su=True), FORM_SCOPE, ts)
        if not py_hmac.compare_digest(expected, sig):
            return False
        try:
            age = time.time() - int(ts)
        except ValueError:
            return False
        return MIN_FORM_SECONDS <= age <= MAX_FORM_SECONDS

    def _page_lang(self):
        return request.lang.code if request.lang else "en_US"

    def _public_module_url(self, module, version):
        """Fiche du module sur le store public, dans la langue de la page."""
        base = (
            request.env["ir.config_parameter"].sudo().get_param(PARAM_STORE_URL)
            or DEFAULT_STORE_URL
        ).rstrip("/")
        prefix = ""
        website = request.website
        if request.lang and website and request.lang.code != website.default_lang_id.code:
            prefix = "/" + request.lang.url_code
        return "%s%s%s?v=%s" % (base, prefix, module.website_url, version)

    def _trial_or_404(self, trial_id, token):
        trial = request.env["oski.module.trial"].sudo().browse(trial_id).exists()
        if not trial or not token or not py_hmac.compare_digest(trial.access_token or "", token):
            return None
        return trial

    def _trial_urls(self, trial):
        # Préfixe de langue explicite : le sondage JS renvoie les messages
        # dans la langue de la page, sans détour par une redirection 303.
        url_for = request.env["ir.http"]._url_for
        base = "/apps/trial/%s/%s" % (trial.id, trial.access_token)
        return {
            "wait_url": url_for(base),
            "status_url": url_for(base + "/status"),
            "open_url": url_for(base + "/open"),
        }

    # ------------------------------------------------------------------
    # Formulaire
    # ------------------------------------------------------------------

    def _render_form(self, module, versions, values=None, error=None, status=200):
        Country = request.env["res.country"].sudo()
        user = request.env.user
        partner = user.partner_id if not user._is_public() else False
        values = dict(values or {})
        if "country_id" not in values:
            country, _source = self._download_country(partner)
            values["country_id"] = country.id if country else False
        if "email" not in values and partner:
            values["email"] = partner.email or ""
        if values.get("version") not in versions:
            values["version"] = (
                DEFAULT_TRIAL_VERSION if DEFAULT_TRIAL_VERSION in versions else versions[0]
            )
        form_ts, form_sig = self._form_stamp()
        response = request.render(
            "oski_app_store.trial_form_page",
            {
                "module": module,
                "versions": versions,
                "countries": Country.search([]),
                "form": values,
                "error": error,
                "form_ts": form_ts,
                "form_sig": form_sig,
                "honeypot_field": HONEYPOT_FIELD,
                "form_action": request.env["ir.http"]._url_for("/apps/trial/start/%s" % module.id),
                "terms_url": request.env["ir.http"]._url_for("/apps/conditions-utilisation"),
                "main_object": module,
                "additional_title": module.name,
            },
        )
        response.status_code = status
        return response

    @http.route(
        ["/apps/trial/start/<int:module_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET", "POST"],
    )
    def apps_trial_start(self, module_id, **post):
        Trial = request.env["oski.module.trial"].sudo()
        module = self._trial_module(module_id)
        if not module or not Trial._is_enabled():
            return request.not_found()
        versions = Trial._trial_versions(module)
        if not versions:
            return request.redirect(module.website_url)

        if request.httprequest.method != "POST":
            return self._render_form(module, versions, {"version": post.get("v")})

        values = {
            "email": (post.get("email") or "").strip()[:254],
            "version": post.get("version"),
            "accept_terms": bool(post.get("accept_terms")),
        }
        try:
            values["country_id"] = int(post.get("country_id") or 0)
        except ValueError:
            values["country_id"] = 0

        # Robots : champ piège rempli ou formulaire envoyé trop vite / jamais affiché.
        if post.get(HONEYPOT_FIELD) or not self._form_stamp_ok(
            post.get("form_ts"), post.get("form_sig")
        ):
            _logger.info("Essai %s : envoi rejeté par le filtre anti-robot", module.technical_name)
            return self._render_form(
                module, versions, values,
                error=request.env._("Please check the form and send it again."),
                status=400,
            )

        email = Trial._normalize_email(values["email"])
        if not email:
            return self._render_form(
                module, versions, values,
                error=request.env._("Please enter a valid e-mail address."), status=400,
            )
        if values["version"] not in versions:
            return self._render_form(
                module, versions, values,
                error=request.env._("Please choose an Odoo version."), status=400,
            )
        if not values["accept_terms"]:
            return self._render_form(
                module, versions, values,
                error=request.env._("Please accept the terms of use."), status=400,
            )

        ip_hash = Trial._hash_ip(request.httprequest.remote_addr)
        refusal = Trial._check_limits(email, ip_hash)
        if refusal:
            return self._render_form(
                module, versions, values, error=Trial._refusal_message(refusal), status=429,
            )

        user = request.env.user
        partner = user.partner_id if not user._is_public() else False
        geo_country, source = self._download_country(partner)
        country = request.env["res.country"].sudo().browse(values["country_id"]).exists()
        if country and country != geo_country:
            source = "form"
        elif not country:
            country = geo_country
        lang = self._page_lang()
        if not partner:
            partner = Trial._find_or_create_partner(email, country=country, lang=lang)
        trial = Trial.create({
            "module_id": module.id,
            "odoo_version": values["version"],
            "lang": lang,
            "email": email,
            "partner_id": partner.id,
            "country_id": country.id if country else False,
            "country_source": source if country else "unknown",
            "ip_hash": ip_hash,
            "buy_url": self._public_module_url(module, values["version"]),
        })
        trial._start()
        return request.redirect(self._trial_urls(trial)["wait_url"])

    # ------------------------------------------------------------------
    # Page d'attente, sondage, ouverture
    # ------------------------------------------------------------------

    @http.route(
        ["/apps/trial/<int:trial_id>/<string:token>"],
        type="http", auth="public", website=True, sitemap=False,
    )
    def apps_trial_wait(self, trial_id, token, **kw):
        trial = self._trial_or_404(trial_id, token)
        if not trial:
            return request.not_found()
        trial._refresh()
        urls = self._trial_urls(trial)
        return request.render(
            "oski_app_store.trial_wait_page",
            {
                "trial": trial,
                "module": trial.module_id,
                "message": trial._visitor_message(),
                "pending": trial.state in ("new", "queued", "building"),
                "auto_open": trial.state == "ready" and not trial.login_used,
                "retry_url": request.env["ir.http"]._url_for(
                    "/apps/trial/start/%s?v=%s" % (trial.module_id.id, trial.odoo_version)
                ),
                "module_url": request.env["ir.http"]._url_for(trial.module_id.website_url),
                "support_url": request.env["ir.http"]._url_for("/apps/support"),
                **urls,
            },
        )

    @http.route(
        ["/apps/trial/<int:trial_id>/<string:token>/status"],
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def apps_trial_status(self, trial_id, token, **kw):
        trial = self._trial_or_404(trial_id, token)
        if not trial:
            return request.make_json_response({"error": "not_found"}, status=404)
        trial._refresh()
        urls = self._trial_urls(trial)
        return request.make_json_response(
            {
                "state": trial.state,
                "message": trial._visitor_message(),
                "pending": trial.state in ("new", "queued", "building"),
                "open_url": urls["open_url"] if trial.state == "ready" else False,
            },
            headers=[("Cache-Control", "no-store")],
        )

    @http.route(
        ["/apps/trial/<int:trial_id>/<string:token>/open"],
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def apps_trial_open(self, trial_id, token, **kw):
        trial = self._trial_or_404(trial_id, token)
        if not trial:
            return request.not_found()
        url = trial._fresh_login_url()
        if not url:
            return request.redirect(self._trial_urls(trial)["wait_url"])
        return request.redirect(url, local=False)

    # ------------------------------------------------------------------
    # Webhook du service (fin d'essai)
    # ------------------------------------------------------------------

    @http.route(
        [WEBHOOK_PATH],
        type="http", auth="public", csrf=False, methods=["POST"], save_session=False,
    )
    def apps_trial_webhook(self, **kw):
        Trial = request.env["oski.module.trial"].sudo()
        body = request.httprequest.get_data()
        headers = request.httprequest.headers
        error = verify_signature(
            Trial._secret(), "POST", WEBHOOK_PATH, body,
            headers.get("X-Oski-Timestamp"), headers.get("X-Oski-Signature"),
        )
        if not error and not request.env["oski.trial.nonce"].sudo()._consume(
            headers.get("X-Oski-Signature")
        ):
            error = "replayed"
        if error:
            _logger.warning("Webhook d'essai refusé : %s", error)
            return request.make_json_response({"error": error}, status=401)
        try:
            payload = json.loads(body or b"{}")
            store_id = int(payload.get("store_trial_id") or 0)
        except (ValueError, TypeError, AttributeError):
            return request.make_json_response({"error": "bad_request"}, status=400)
        trial = Trial.browse(store_id).exists()
        if not trial or (
            trial.remote_trial_id and payload.get("trial_id")
            and trial.remote_trial_id != payload["trial_id"]
        ):
            return request.make_json_response({"error": "not_found"}, status=404)
        if payload.get("event") not in ("trial.expired", "trial.failed"):
            return request.make_json_response({"ok": True, "ignored": True})
        trial._close_from_webhook(payload)
        return request.make_json_response({"ok": True})
