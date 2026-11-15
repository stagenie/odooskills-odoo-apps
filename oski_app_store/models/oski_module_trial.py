"""Essai 1 h d'un module payant : demande côté store, base éphémère côté VPS démo.

Le store ne fait que trois choses : filtrer la demande (e-mail, limites, robots),
appeler le service d'essai par requêtes signées (HMAC, secret partagé dans
`ir.config_parameter`, jamais dans le code), et clore l'essai sur le webhook
d'expiration en envoyant un seul courriel avec le lien d'achat.

Contrat du service : docs/appstore/essai-1h/API.md (dépôt odoo20-dev).
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta

import requests
from babel.dates import format_date as babel_format_date

from odoo import _, api, fields, models
from odoo.tools import email_normalize, format_amount
from odoo.tools.misc import babel_locale_parse

_logger = logging.getLogger(__name__)

PARAM_ENABLED = "oski.trial.enabled"
PARAM_API_URL = "oski.trial.api_url"
PARAM_SECRET = "oski.trial.secret"
PARAM_IP_SALT = "oski.trial.ip_salt"
PARAM_STORE_URL = "oski.trial.store_url"
DEFAULT_API_URL = "https://trial.lab.odooskills.com"
DEFAULT_STORE_URL = "https://apps.odooskills.com"

# Versions servies par le service d'essai (API.md § 2, `versions`).
TRIAL_VERSIONS = ("20.0", "19.0", "18.0")
DEFAULT_TRIAL_VERSION = "20.0"

MAX_PER_IP_PER_DAY = 3
SIGNATURE_WINDOW = 300          # ± secondes acceptées sur l'horodatage
NONCE_TTL = 600                 # anti-rejeu : signatures gardées 10 min
HTTP_TIMEOUT = 15

ACTIVE_STATES = ("new", "queued", "building", "ready")
PENDING_STATES = ("queued", "building")


def sign(secret, method, path, body, ts):
    """Signature HMAC du service d'essai (API.md § 1).

    message = ``ts\\nMETHODE\\nchemin\\nsha256_hex(corps)`` ; rend l'hexadécimal.
    """
    if isinstance(secret, str):
        secret = secret.encode()
    digest = hashlib.sha256(body or b"").hexdigest()
    message = f"{int(ts)}\n{method.upper()}\n{path}\n{digest}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _parse_utc(value):
    """`AAAA-MM-JJTHH:MM:SSZ` → datetime naïf UTC (convention Odoo), sinon False."""
    if not value:
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return False


class TrialServiceError(Exception):
    """Le service d'essai n'a pas pu être joint ou a répondu hors contrat."""


class OskiModuleTrial(models.Model):
    _name = "oski.module.trial"
    _description = "Store 1-hour trial"
    _order = "create_date desc, id desc"
    _rec_name = "email"

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade", index=True
    )
    odoo_version = fields.Char(string="Odoo version", required=True)
    lang = fields.Char(string="Language", help="Starting language of the trial database.")
    email = fields.Char(string="E-mail", required=True, index=True)
    partner_id = fields.Many2one(
        "res.partner", string="Contact", ondelete="set null", index=True
    )
    country_id = fields.Many2one(
        "res.country", string="Country", ondelete="set null", index=True
    )
    country_source = fields.Selection(
        [
            ("partner", "Customer address"),
            ("geoip", "Geolocation"),
            ("form", "Chosen by visitor"),
            ("unknown", "Unknown"),
        ],
        string="Country source",
        default="unknown",
        required=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("queued", "Queued"),
            ("building", "Building"),
            ("ready", "Ready"),
            ("expired", "Ended"),
            ("failed", "Failed"),
            ("error", "Not started"),
        ],
        string="Status",
        default="new",
        required=True,
        index=True,
    )
    phase = fields.Char(string="Build phase")
    queue_position = fields.Integer(string="Queue position")
    error_code = fields.Char(string="Error code")
    remote_trial_id = fields.Char(string="Service trial ID", copy=False, index=True)
    expires_at = fields.Datetime(string="Expires at")
    ready_at = fields.Datetime(string="Ready at")
    ended_at = fields.Datetime(string="Ended at")
    login_url = fields.Char(
        string="Login link",
        copy=False,
        groups="base.group_system",
        help="Single-use login link of the trial database. Never e-mailed nor logged.",
    )
    login_used = fields.Boolean(string="Login link used", copy=False)
    buy_url = fields.Char(string="Purchase link")
    ip_hash = fields.Char(
        string="Connection fingerprint",
        index=True,
        copy=False,
        help="Salted SHA-256 of the visitor IP address. The address itself is never stored.",
    )
    access_token = fields.Char(
        string="Access token",
        copy=False,
        groups="base.group_system",
        default=lambda self: secrets.token_urlsafe(24),
    )
    end_mail_sent = fields.Boolean(string="End e-mail sent", copy=False)
    pricing_note = fields.Char(
        string="Launch offer", compute="_compute_pricing_note"
    )
    remaining_minutes = fields.Integer(
        string="Minutes left", compute="_compute_remaining_minutes"
    )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------

    @api.depends("expires_at", "state")
    def _compute_remaining_minutes(self):
        now = fields.Datetime.now()
        for trial in self:
            if trial.state == "ready" and trial.expires_at and trial.expires_at > now:
                trial.remaining_minutes = int((trial.expires_at - now).total_seconds() // 60)
            else:
                trial.remaining_minutes = 0

    @api.depends("module_id")
    @api.depends_context("lang")
    def _compute_pricing_note(self):
        for trial in self:
            trial.pricing_note = trial._launch_offer_note()

    def _launch_offer_note(self):
        """Phrase « prix de lancement » lue sur la liste de prix du site, ou "".

        Hors requête HTTP (webhook) : la liste de prix du site est retrouvée
        par son `website_id`, la plus prioritaire d'abord — la même que celle
        que le panier appliquera.
        """
        self.ensure_one()
        product = self.module_id.sudo().product_tmpl_id
        variant = product.product_variant_id
        if not variant:
            return ""
        website = self.env["website"].sudo().search([], limit=1)
        pricelist = self.env["product.pricelist"].sudo().search(
            [("website_id", "in", [website.id, False])], order="sequence, id", limit=1
        ) if website else False
        if not pricelist:
            return ""
        price, rule_id = pricelist._get_product_price_rule(variant, 1.0)
        list_price = product.list_price
        if not list_price or price >= list_price:
            return ""
        rule = self.env["product.pricelist.item"].sudo().browse(rule_id)
        percent = round(100.0 * (1.0 - price / list_price))
        lang = self.env.lang or "en_US"
        amount = format_amount(self.env, price, pricelist.currency_id, lang_code=lang)
        if rule.date_end:
            date_label = babel_format_date(
                rule.date_end.date(), format="long", locale=babel_locale_parse(lang)
            )
            return _(
                "Launch price: %(amount)s (%(percent)s%% off) until %(date)s.",
                amount=amount,
                percent=percent,
                date=date_label,
            )
        return _("Launch price: %(amount)s (%(percent)s%% off).", amount=amount, percent=percent)

    # ------------------------------------------------------------------
    # Paramètres
    # ------------------------------------------------------------------

    @api.model
    def _param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default) or default

    @api.model
    def _is_enabled(self):
        """Lancement maîtrisé : le bouton n'existe que si le paramètre vaut vrai."""
        return self._param(PARAM_ENABLED, "False").strip().lower() in ("1", "true", "yes")

    @api.model
    def _secret(self):
        return self._param(PARAM_SECRET).strip()

    @api.model
    def _hash_ip(self, ip):
        """Empreinte salée de l'adresse IP ; le sel est tiré une fois par base."""
        if not ip:
            return False
        Param = self.env["ir.config_parameter"].sudo()
        salt = Param.get_param(PARAM_IP_SALT)
        if not salt:
            salt = secrets.token_hex(32)
            Param.set_param(PARAM_IP_SALT, salt)
        return hashlib.sha256(("%s|%s" % (salt, ip)).encode()).hexdigest()

    # ------------------------------------------------------------------
    # Modules et versions éligibles
    # ------------------------------------------------------------------

    @api.model
    def _trial_versions(self, module):
        """Versions Odoo proposables à l'essai : archive présente et service prêt.

        Plus récente d'abord ; la 20.0 en tête dès qu'elle a une archive.
        """
        module = module.sudo()
        if not module or module.is_free or not module.is_published:
            return []
        available = {
            line.odoo_version for line in module.version_line_ids if line.attachment_id
        }
        return [v for v in TRIAL_VERSIONS if v in available]

    # ------------------------------------------------------------------
    # Limites (spéc. : 1 essai actif par e-mail, 3 par IP / 24 h)
    # ------------------------------------------------------------------

    @api.model
    def _active_for_email(self, email):
        now = fields.Datetime.now()
        trials = self.sudo().search([("email", "=", email), ("state", "in", ACTIVE_STATES)])
        return trials.filtered(lambda t: not t.expires_at or t.expires_at > now)[:1]

    @api.model
    def _count_for_ip(self, ip_hash):
        if not ip_hash:
            return 0
        since = fields.Datetime.now() - timedelta(hours=24)
        return self.sudo().search_count(
            [("ip_hash", "=", ip_hash), ("create_date", ">=", since)]
        )

    @api.model
    def _check_limits(self, email, ip_hash):
        """None si la demande passe, sinon le code de refus."""
        if self._active_for_email(email):
            return "already_active"
        if self._count_for_ip(ip_hash) >= MAX_PER_IP_PER_DAY:
            return "ip_limit"
        return None

    # ------------------------------------------------------------------
    # Langue
    # ------------------------------------------------------------------

    @api.model
    def _normalize_lang(self, code):
        """Code de langue Odoo actif (« en » → « en_US ») ; « en_US » à défaut.

        `lang` sert de langue au courriel de fin : un code court y lève
        « Invalid language code » et fait échouer le webhook (422).
        """
        Lang = self.env["res.lang"].sudo()
        code = (code or "").strip().replace("-", "_")
        if code and Lang._lang_get(code):
            return code
        prefix = code.split("_")[0].lower()
        if prefix:
            for lang_code, _name in Lang.get_installed():
                if lang_code.split("_")[0].lower() == prefix:
                    return lang_code
        return "en_US"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "lang" in vals:
                vals["lang"] = self._normalize_lang(vals["lang"])
        return super().create(vals_list)

    def write(self, vals):
        if "lang" in vals:
            vals = dict(vals, lang=self._normalize_lang(vals["lang"]))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    @api.model
    def _find_or_create_partner(self, email, country=False, lang=False):
        Partner = self.env["res.partner"].sudo()
        partner = Partner.search([("email_normalized", "=", email)], limit=1)
        if partner:
            if country and not partner.country_id:
                partner.country_id = country
            return partner
        values = {"name": email, "email": email, "country_id": country.id if country else False}
        if lang and self.env["res.lang"]._lang_get(lang):
            values["lang"] = lang
        return Partner.create(values)

    @api.model
    def _normalize_email(self, email):
        return email_normalize(email or "", strict=True) or False

    # ------------------------------------------------------------------
    # Appels au service d'essai
    # ------------------------------------------------------------------

    @api.model
    def _service_call(self, method, path, payload=None):
        """Requête signée vers le service ; rend (statut HTTP, corps JSON).

        Chaque requête est signée à nouveau (anti-rejeu du service).
        Lève TrialServiceError si le service est injoignable ou non configuré.
        """
        secret = self._secret()
        if not secret:
            raise TrialServiceError("trial secret not configured")
        base = self._param(PARAM_API_URL, DEFAULT_API_URL).rstrip("/")
        body = json.dumps(payload).encode() if payload is not None else b""
        ts = int(time.time())
        headers = {
            "X-Oski-Timestamp": str(ts),
            "X-Oski-Signature": "sha256=%s" % sign(secret, method, path, body, ts),
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(
                method, base + path, data=body or None, headers=headers, timeout=HTTP_TIMEOUT
            )
        except requests.RequestException as exc:
            raise TrialServiceError(str(exc)) from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 500 and response.status_code != 503:
            raise TrialServiceError("HTTP %s" % response.status_code)
        if response.status_code == 401:
            # Mauvais secret ou horloge : jamais la faute du visiteur.
            _logger.error("Trial service: signature rejected (%s)", data.get("error"))
            raise TrialServiceError("signature refused")
        return response.status_code, data

    def _apply_remote(self, data):
        """Recopie l'objet *Essai* du service (API.md § 3) sur l'enregistrement."""
        self.ensure_one()
        status = data.get("status")
        values = {}
        if data.get("trial_id"):
            values["remote_trial_id"] = data["trial_id"]
        if status in ("queued", "building", "ready", "expired", "failed"):
            values["state"] = status
        values["queue_position"] = data.get("queue_position") or 0
        values["phase"] = data.get("phase") or False
        if data.get("expires_at"):
            values["expires_at"] = _parse_utc(data["expires_at"])
        if status == "ready":
            if not self.ready_at:
                values["ready_at"] = fields.Datetime.now()
            if data.get("login_url"):
                values["login_url"] = data["login_url"]
        if status == "failed":
            values["error_code"] = data.get("error") or "build_failed"
        self.sudo().write(values)

    def _start(self):
        """POST /trial ; l'essai passe en file, en préparation, ou en erreur."""
        self.ensure_one()
        trial = self.sudo()
        payload = {
            "module": trial.module_id.technical_name,
            "version": trial.odoo_version,
            "lang": trial.lang or "en",
            "email": trial.email,
            "store_trial_id": str(trial.id),
            "buy_url": trial.buy_url or DEFAULT_STORE_URL + "/apps",
            "module_name": (trial.module_id.with_context(lang="en_US").name or "")[:120],
        }
        try:
            status, data = self._service_call("POST", "/trial", payload)
        except TrialServiceError as exc:
            _logger.warning("Essai %s : service injoignable (%s)", trial.id, exc)
            trial.write({"state": "error", "error_code": "unavailable"})
            return
        if status in (200, 202):
            trial._apply_remote(data)
            return
        code = data.get("error") or "http_%s" % status
        _logger.info("Trial %s rejected by the service: %s %s", trial.id, status, code)
        trial.write({"state": "error", "error_code": code})

    def _refresh(self):
        """GET /trial/<id> tant que l'essai attend ; silencieux si le service tousse."""
        self.ensure_one()
        trial = self.sudo()
        if trial.state not in PENDING_STATES or not trial.remote_trial_id:
            return
        try:
            status, data = self._service_call("GET", "/trial/%s" % trial.remote_trial_id)
        except TrialServiceError as exc:
            _logger.warning("Essai %s : sondage impossible (%s)", trial.id, exc)
            return
        if status == 200:
            trial._apply_remote(data)
        elif status == 404:
            trial.write({"state": "failed", "error_code": "not_found"})

    def _fresh_login_url(self):
        """Lien d'ouverture : le lien reçu la première fois, un nouveau ensuite.

        Le lien du service est à usage unique ; « Rouvrir ma base » demande
        donc un nouveau jeton (POST /trial/<id>/login), qui invalide l'ancien.
        """
        self.ensure_one()
        trial = self.sudo()
        if trial.state != "ready":
            return False
        if trial.login_url and not trial.login_used:
            trial.login_used = True
            return trial.login_url
        try:
            status, data = self._service_call(
                "POST", "/trial/%s/login" % trial.remote_trial_id
            )
        except TrialServiceError as exc:
            _logger.warning("Trial %s: new link failed (%s)", trial.id, exc)
            return False
        if status == 200 and data.get("login_url"):
            trial._apply_remote(data)
            trial.login_used = True
            return data["login_url"]
        if status == 409:
            trial._refresh_state_after_conflict(data)
        return False

    def _refresh_state_after_conflict(self, data):
        """409 not_ready : l'essai n'est plus prêt (expiré entre-temps)."""
        self.ensure_one()
        if self.expires_at and self.expires_at <= fields.Datetime.now():
            self.sudo().write({"state": "expired", "ended_at": fields.Datetime.now()})

    # ------------------------------------------------------------------
    # Message honnête affiché au visiteur
    # ------------------------------------------------------------------

    def _visitor_message(self):
        self.ensure_one()
        state = self.state
        if state == "queued":
            if self.queue_position:
                return _(
                    "%(count)s person(s) ahead of you. A running trial frees its place "
                    "within 1 hour at the latest.",
                    count=self.queue_position,
                )
            return _("You are in the queue. A running trial frees its place within 1 hour at the latest.")
        if state in ("new", "building"):
            if self.phase == "template":
                return _(
                    "Preparing your database… This is the first trial of this module on "
                    "this Odoo version: it takes 1 to 5 minutes."
                )
            return _("Preparing your database… It takes a few seconds.")
        if state == "ready":
            return _("Your database is ready. Opening it…")
        if state == "expired":
            return _("This trial has ended. The database has been deleted.")
        if state == "failed":
            return _(
                "We could not build your database. Try another Odoo version, "
                "or contact support."
            )
        return self._refusal_message(self.error_code)

    @api.model
    def _refusal_message(self, code):
        if code == "already_active":
            return _(
                "A trial is already running for this e-mail address. Only one trial "
                "at a time: wait until it ends (1 hour at most)."
            )
        if code == "ip_limit":
            return _(
                "Too many trials from your connection in the last 24 hours. "
                "Please try again tomorrow."
            )
        if code == "queue_full":
            return _(
                "The trial queue is full for this Odoo version. Please try again "
                "later, or choose another version."
            )
        if code in ("bad_version", "unknown_module", "not_paid"):
            return _(
                "This module cannot be tried on this Odoo version yet. "
                "Choose another version, or contact support."
            )
        return _(
            "The trial service is not available right now. Please try again in a few minutes."
        )

    # ------------------------------------------------------------------
    # Fin d'essai (webhook)
    # ------------------------------------------------------------------

    def _close_from_webhook(self, payload):
        """Applique `trial.expired` / `trial.failed` ; courriel une seule fois."""
        self.ensure_one()
        trial = self.sudo()
        event = payload.get("event")
        values = {}
        if payload.get("trial_id") and not trial.remote_trial_id:
            values["remote_trial_id"] = payload["trial_id"]
        ready_at = _parse_utc(payload.get("ready_at"))
        if ready_at and not trial.ready_at:
            values["ready_at"] = ready_at
        values["ended_at"] = _parse_utc(payload.get("ended_at")) or fields.Datetime.now()
        if event == "trial.failed":
            values.update(state="failed", error_code=payload.get("error") or "build_failed")
        else:
            values["state"] = "expired"
        trial.write(values)
        if trial.state == "expired" and trial.ready_at and not trial.end_mail_sent:
            trial._send_end_mail()

    def _send_end_mail(self):
        self.ensure_one()
        template = self.env.ref("oski_app_store.mail_template_trial_ended", raise_if_not_found=False)
        if not template:
            return
        # Drapeau posé avant l'envoi : un webhook réémis ne double jamais le courriel.
        self.sudo().end_mail_sent = True
        template.sudo().send_mail(self.id, force_send=False)


class OskiTrialNonce(models.Model):
    """Signatures de webhook déjà reçues (anti-rejeu, 10 min)."""

    _name = "oski.trial.nonce"
    _description = "Trial webhook signature seen"

    signature = fields.Char(required=True, index=True)

    _signature_uniq = models.Constraint("UNIQUE(signature)", "Signature already received.")

    @api.model
    def _consume(self, signature):
        """True la première fois qu'une signature est vue, False si rejouée."""
        limit = fields.Datetime.now() - timedelta(seconds=NONCE_TTL)
        self.sudo().search([("create_date", "<", limit)]).unlink()
        if self.sudo().search_count([("signature", "=", signature)]):
            return False
        self.sudo().create({"signature": signature})
        return True


def verify_signature(secret, method, path, body, ts_header, sig_header, now=None):
    """Contrôle d'une requête signée entrante ; rend None si valide, sinon le code."""
    if not secret:
        return "not_configured"
    try:
        ts = int(ts_header)
    except (TypeError, ValueError):
        return "bad_signature"
    now = time.time() if now is None else now
    if abs(now - ts) > SIGNATURE_WINDOW:
        return "stale_request"
    sig = (sig_header or "").strip()
    if sig.startswith("sha256="):
        sig = sig[len("sha256="):]
    expected = sign(secret, method, path, body, ts)
    if not hmac.compare_digest(expected, sig):
        return "bad_signature"
    return None
