"""Comptage des vues de fiche et filtre des robots pour les compteurs du store.

Une vue est comptée au plus une fois par module et par session dans la
fenêtre `VIEW_COUNT_GUARD_SECONDS`. Jamais comptés : robots et clients non
navigateurs (motif `ROBOT_UA_RE` sur l'en-tête User-Agent, User-Agent vide
compris), utilisateurs internes (équipe, gestionnaires du store). Le même filtre
s'applique aux téléchargements : la vérification automatique des fiches
(`publish_check`, curl…) ne gonfle plus le compteur public.

`python-requests` n'est volontairement PAS dans le motif : c'est le client des
HttpCase d'Odoo, et `authenticate()` y recrée la session HTTP (en-têtes perdus) ;
le filtrer imposerait de retoucher toutes les suites de téléchargement.
"""
import logging
import re
import time

from odoo import http
from odoo.http import request
from odoo.addons.oski_app_store.controllers.main import OskiAppStore

_logger = logging.getLogger(__name__)

VIEW_COUNT_GUARD_SECONDS = 30 * 60

ROBOT_UA_RE = re.compile(
    r"bot|crawl|spider|slurp|scrap|ia_archive|headless|lighthouse|pingdom|uptime|"
    r"monitor|preview|facebookexternalhit|embedly|python-urllib|curl/|wget/|httpx|"
    r"aiohttp|go-http|okhttp|java/|libwww|axios|node-fetch|postman|publish_check",
    re.IGNORECASE,
)


def is_robot_or_internal():
    """True si la requête courante ne doit alimenter aucun compteur."""
    user_agent = request.httprequest.headers.get("User-Agent", "")
    if not user_agent.strip() or ROBOT_UA_RE.search(user_agent):
        return True
    user = request.env.user
    return bool(user) and not user._is_public() and user._is_internal()


class OskiAppStoreStats(OskiAppStore):

    def _should_count_download(self, version_id):
        if is_robot_or_internal():
            return False
        return super()._should_count_download(version_id)

    def _should_count_view(self, module_id):
        """Garde de session : une vue par module et par fenêtre de 30 min."""
        if is_robot_or_internal():
            return False
        key = str(module_id)
        now = time.time()
        seen = {
            k: ts
            for k, ts in (request.session.get("oski_view_counted") or {}).items()
            if now - ts < VIEW_COUNT_GUARD_SECONDS
        }
        should_count = key not in seen
        if should_count:
            seen[key] = now
            request.session["oski_view_counted"] = seen
        return should_count

    def _view_country_id(self):
        try:
            code = request.geoip.country_code
        except Exception:  # noqa: BLE001 — la géoloc ne doit jamais bloquer la fiche
            code = None
        if not code:
            return None
        country = request.env["res.country"].sudo().search(
            [("code", "=", code.upper())], limit=1
        )
        return country.id or None

    def _log_view(self, module):
        try:
            if not module.sudo().is_published or not self._should_count_view(module.id):
                return
            with request.env.cr.savepoint():
                request.env["oski.module.view.daily"].sudo()._record_view(
                    module.id, self._view_country_id()
                )
        except Exception:  # noqa: BLE001 — la fiche doit toujours s'afficher
            _logger.exception("View of module %s not tracked", module.id)

    @http.route()
    def apps_module_page(self, module, v=None, **kw):
        response = super().apps_module_page(module, v=v, **kw)
        if getattr(response, "status_code", 200) == 200:
            self._log_view(module)
        return response
