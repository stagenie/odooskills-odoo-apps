from odoo import fields, models


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _description = "Équipe d'assistance"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    member_ids = fields.Many2many("res.users", string="Membres")
    assignment_method = fields.Selection(
        [("manual", "Manuelle"), ("balanced", "Équilibrée (par charge)")],
        string="Méthode d'assignation", default="manual", required=True)
    stage_ids = fields.Many2many("helpdesk.stage", string="Étapes")
    company_id = fields.Many2one(
        "res.company", string="Société",
        default=lambda self: self.env.company)
