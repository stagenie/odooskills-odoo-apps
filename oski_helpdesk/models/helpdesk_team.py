from odoo import api, fields, models


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
    ticket_count = fields.Integer(string="Tickets", compute="_compute_ticket_count")

    def _compute_ticket_count(self):
        data = self.env["helpdesk.ticket"]._read_group(
            [("team_id", "in", self.ids)], ["team_id"], ["__count"])
        mapped = {team.id: count for team, count in data}
        for team in self:
            team.ticket_count = mapped.get(team.id, 0)
