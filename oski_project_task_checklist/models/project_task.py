from odoo import api, fields, models


class ProjectTask(models.Model):
    """Ajoute une checklist d'étapes et un indicateur d'avancement à la tâche."""

    _inherit = "project.task"

    oski_checklist_ids = fields.One2many(
        "oski.task.checklist.item",
        "task_id",
        string="Checklist",
    )
    oski_checklist_progress = fields.Float(
        string="Checklist Progress",
        compute="_compute_oski_checklist_progress",
        store=True,
        help="Percentage of completed steps in the task checklist.",
    )
    oski_checklist_count = fields.Integer(
        string="Number of Steps",
        compute="_compute_oski_checklist_progress",
        store=True,
    )

    @api.depends("oski_checklist_ids", "oski_checklist_ids.done")
    def _compute_oski_checklist_progress(self):
        """Calcule le pourcentage d'étapes faites (0.0 si aucune étape)."""
        for task in self:
            items = task.oski_checklist_ids
            count = len(items)
            task.oski_checklist_count = count
            if not count:
                task.oski_checklist_progress = 0.0
                continue

            done = len(items.filtered("done"))
            task.oski_checklist_progress = (done / count) * 100.0
