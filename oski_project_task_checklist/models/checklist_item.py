from odoo import fields, models


class OskiTaskChecklistItem(models.Model):
    """Étape de checklist rattachée à une tâche de projet."""

    _name = "oski.task.checklist.item"
    _description = "Étape de checklist de tâche"
    _order = "sequence, id"

    task_id = fields.Many2one(
        "project.task",
        string="Tâche",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Étape", required=True)
    done = fields.Boolean(string="Fait")
    sequence = fields.Integer(string="Séquence", default=10)
    user_id = fields.Many2one("res.users", string="Assigné à")
