from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _description = "Ticket d'assistance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, id desc"

    name = fields.Char(string="Sujet", required=True, tracking=True)
    number = fields.Char(string="Numéro", readonly=True, copy=False, default="/")
    team_id = fields.Many2one("helpdesk.team", string="Équipe", required=True, tracking=True)
    stage_id = fields.Many2one(
        "helpdesk.stage", string="Étape", tracking=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage_id())
    user_id = fields.Many2one("res.users", string="Assigné à", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Client")
    partner_email = fields.Char(string="Courriel")
    priority = fields.Selection(
        [("0", "Basse"), ("1", "Normale"), ("2", "Haute"), ("3", "Urgente")],
        string="Priorité", default="1")
    kanban_state = fields.Selection(
        [("normal", "En cours"), ("done", "Prêt"), ("blocked", "Bloqué")],
        string="État", default="normal")
    tag_ids = fields.Many2many("helpdesk.tag", string="Étiquettes")
    description = fields.Html(string="Description")
    color = fields.Integer(string="Couleur")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.model
    def _default_stage_id(self):
        return self.env["helpdesk.stage"].search([], order="sequence, id", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env["helpdesk.stage"].search([], order="sequence, id")

    def _assign_balanced(self, team):
        members = team.member_ids
        if not members:
            return self.env["res.users"]
        counts = {m.id: 0 for m in members}
        data = self._read_group(
            [("team_id", "=", team.id),
             ("user_id", "in", members.ids),
             ("stage_id.is_close", "=", False)],
            ["user_id"], ["__count"])
        for user, count in data:
            counts[user.id] = count
        best_id = min(members.ids, key=lambda uid: counts.get(uid, 0))
        return self.env["res.users"].browse(best_id)

    @api.model_create_multi
    def create(self, vals_list):
        teams = self.env["helpdesk.team"].browse(
            [v.get("team_id") for v in vals_list if v.get("team_id")])
        team_map = {t.id: t for t in teams}
        for vals in vals_list:
            if not vals.get("number") or vals["number"] == "/":
                vals["number"] = self.env["ir.sequence"].sudo().next_by_code(
                    "helpdesk.ticket") or "/"
            team = team_map.get(vals.get("team_id"))
            if team and team.assignment_method == "balanced" and not vals.get("user_id"):
                user = self._assign_balanced(team)
                if user:
                    vals["user_id"] = user.id
        return super().create(vals_list)
