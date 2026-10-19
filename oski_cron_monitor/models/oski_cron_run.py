from datetime import timedelta

from odoo import api, fields, models

DEFAULT_RETENTION_DAYS = 30
GC_LIMIT = 5000


class OskiCronRun(models.Model):
    _name = "oski.cron.run"
    _description = "Exécution d'une tâche planifiée"
    _order = "started_at desc, id desc"
    _rec_name = "cron_name"

    # La tâche peut disparaître (module désinstallé, action supprimée) sans que
    # son histoire perde son intérêt : le nom est recopié, et le lien se dénoue
    # au lieu d'emporter les lignes.
    cron_id = fields.Many2one("ir.cron", string="Tâche planifiée", ondelete="set null", index=True)
    cron_name = fields.Char(string="Tâche", required=True, index=True)
    started_at = fields.Datetime(string="Début", required=True, index=True)
    duration = fields.Float(string="Durée (s)", digits=(10, 3))
    state = fields.Selection(
        [("success", "Réussite"), ("failure", "Échec")],
        string="Résultat",
        required=True,
        index=True,
    )
    error = fields.Text(string="Erreur")
    user_id = fields.Many2one("res.users", string="Exécutée en tant que")

    @api.autovacuum
    def _gc_oski_cron_runs(self):
        """Purge les exécutions au-delà de la rétention.

        Une tâche qui tourne toutes les minutes produit un demi-million de
        lignes par an : sans purge, le module deviendrait le problème qu'il
        cherche à révéler.
        """
        days = self.env["ir.config_parameter"].sudo().get_param(
            "oski_cron_monitor.retention_days", DEFAULT_RETENTION_DAYS)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = DEFAULT_RETENTION_DAYS
        if days <= 0:
            return
        limit_date = fields.Datetime.now() - timedelta(days=days)
        stale = self.search([("started_at", "<", limit_date)], limit=GC_LIMIT)
        stale.unlink()
