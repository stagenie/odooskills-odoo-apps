from odoo import api, fields, models


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _description = "Équipe d'assistance"
    _inherit = ["mail.alias.mixin.optional"]
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    use_alias = fields.Boolean(string="Activer l'alias email")
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

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get_id("helpdesk.ticket")
        if self.id:
            values["alias_defaults"] = {"team_id": self.id}
        return values
