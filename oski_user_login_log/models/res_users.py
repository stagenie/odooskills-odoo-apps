import logging

from odoo import SUPERUSER_ID, api, models
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _oski_write_login_log(self, login, result, ip_address, uid=None):
        """Inscrit la tentative sur une transaction qui lui est propre.

        Un échec d'authentification remonte en ``AccessDenied`` et annule la
        transaction de la requête : une trace posée dedans disparaîtrait avec
        elle. Les réussites empruntent le même chemin, pour que le registre
        n'ait qu'un seul comportement à expliquer.
        """
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["oski.login.log"].create({
                "login": login or "(vide)",
                "user_id": uid or False,
                "result": result,
                "ip_address": ip_address,
            })

    def _oski_try_write_login_log(self, login, result, ip_address, uid=None):
        """Enveloppe le registre : il ne doit jamais empêcher quelqu'un d'entrer.

        Le garde-fou entoure l'**appel**, pas le corps de l'écriture : une
        panne du registre, quelle qu'en soit la cause — base saturée, table
        absente, surcharge d'un autre module — laisse la connexion aboutir et
        part dans le journal du serveur.
        """
        try:
            self._oski_write_login_log(login, result, ip_address, uid=uid)
        except Exception:  # noqa: BLE001 - jamais au prix d'une connexion
            _logger.exception("Journal des connexions : écriture impossible")

    def _login(self, credential, user_agent_env):
        login = credential.get("login")
        ip_address = request.httprequest.environ.get("REMOTE_ADDR") if request else False
        try:
            auth_info = super()._login(credential, user_agent_env)
        except AccessDenied:
            self._oski_try_write_login_log(login, "failure", ip_address)
            raise
        self._oski_try_write_login_log(login, "success", ip_address, uid=auth_info["uid"])
        return auth_info
