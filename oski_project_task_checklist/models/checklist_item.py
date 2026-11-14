from odoo import fields, models


class OskiTaskChecklistItem(models.Model):
    """Étape de checklist rattachée à une tâche de projet."""

    _name = "oski.task.checklist.item"
    _description = "Task Checklist Step"
    _order = "sequence, id"

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Step", required=True)
    done = fields.Boolean(string="Done")
    sequence = fields.Integer(string="Sequence", default=10)
    user_id = fields.Many2one(
        "res.users",
        string="Assigned to",
        domain=[("share", "=", False)],
        help="Only an internal user can be assigned a step.",
    )
