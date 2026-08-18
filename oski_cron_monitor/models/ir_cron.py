import logging
import time
import traceback
from contextlib import contextmanager

from odoo import SUPERUSER_ID, api, fields, models

_logger = logging.getLogger(__name__)

ERROR_MAX = 4000


class IrCron(models.Model):
    _inherit = "ir.cron"

    oski_run_ids = fields.One2many("oski.cron.run", "cron_id", string="Exécutions")
    # Trois champs calculés ensemble, et sans ``related`` : un ``related`` posé
    # sur un calcul non stocké fait réclamer à Odoo un champ « searchable » et
    # laisse un avertissement à chaque écriture sur une tâche planifiée.
    oski_last_run_id = fields.Many2one(
        "oski.cron.run", string="Dernière exécution", compute="_compute_oski_last_run")
    oski_last_state = fields.Selection(
        [("success", "Réussite"), ("failure", "Échec")],
        string="Dernier résultat", compute="_compute_oski_last_run")
    oski_last_duration = fields.Float(
        string="Dernière durée (s)", digits=(10, 3), compute="_compute_oski_last_run")

    def _compute_oski_last_run(self):
        runs = self.env["oski.cron.run"].search([("cron_id", "in", self.ids)], order="started_at desc, id desc")
        last_by_cron = {}
        for run in runs:
            last_by_cron.setdefault(run.cron_id.id, run)
        for cron in self:
            last = last_by_cron.get(cron.id)
            cron.oski_last_run_id = last or False
            cron.oski_last_state = last.state if last else False
            cron.oski_last_duration = last.duration if last else 0.0

    @contextmanager
    def _oski_run_env(self):
        """Ouvre l'environnement d'écriture du journal.

        Sur un curseur qui lui est propre : ``_callback`` annule la transaction
        de la tâche quand celle-ci lève, et une trace posée dedans partirait
        avec elle — or l'échec est justement ce qu'on veut garder. Les
        réussites empruntent le même chemin, pour que le registre n'ait qu'un
        seul comportement à expliquer.
        """
        with self.env.registry.cursor() as cr:
            yield api.Environment(cr, SUPERUSER_ID, {})

    def _oski_log_run(self, started_at, duration, state, error=None):
        with self._oski_run_env() as env:
            env["oski.cron.run"].create({
                "cron_id": self.id,
                "cron_name": self.cron_name or self.display_name or str(self.id),
                "started_at": started_at,
                "duration": duration,
                "state": state,
                "error": (error or "")[:ERROR_MAX] or False,
                "user_id": self.user_id.id or False,
            })

    def _oski_try_log_run(self, started_at, duration, state, error=None):
        """Le registre ne doit jamais faire échouer une tâche qui a réussi."""
        try:
            self._oski_log_run(started_at, duration, state, error=error)
        except Exception:  # noqa: BLE001 - jamais au prix d'une tâche
            _logger.exception("Moniteur des tâches planifiées : écriture impossible")

    def _callback(self, cron_name, server_action_id):
        started_at = fields.Datetime.now()
        clock = time.monotonic()
        try:
            result = super()._callback(cron_name, server_action_id)
        except Exception as error:
            self._oski_try_log_run(
                started_at, time.monotonic() - clock, "failure",
                error="%s\n%s" % (error, traceback.format_exc()))
            raise
        self._oski_try_log_run(started_at, time.monotonic() - clock, "success")
        return result
