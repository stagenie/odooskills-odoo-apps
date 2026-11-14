from odoo import fields, models


class HelpdeskStage(models.Model):
    _name = "helpdesk.stage"
    _description = "Helpdesk Stage"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
    fold = fields.Boolean(string="Folded in Kanban")
    is_close = fields.Boolean(
        string="Closing Stage",
        help="Tickets in this stage are considered solved.")
