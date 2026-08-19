from odoo import _, api, fields, models


class CrmLostReason(models.Model):
    """Le motif ne vaut que par ce qu'il coûte.

    Odoo compte les opportunités par motif ; il ne dit pas ce que chacun
    emporte. « Prix trop élevé » sur deux affaires de mille euros et sur une
    de deux cent mille n'appelle pas la même réaction.
    """

    _inherit = "crm.lost.reason"

    oski_lost_revenue = fields.Monetary(
        string="Revenu perdu", compute="_compute_oski_lost",
        currency_field="oski_currency_id")
    oski_last_lost_on = fields.Date(
        string="Dernière perte", compute="_compute_oski_lost")
    oski_currency_id = fields.Many2one(
        "res.currency", compute="_compute_oski_currency")

    def _compute_oski_currency(self):
        for reason in self:
            reason.oski_currency_id = self.env.company.currency_id

    @api.depends()
    def _compute_oski_lost(self):
        grouped = self.env["crm.lead"].with_context(active_test=False)._read_group(
            [("lost_reason_id", "in", self.ids)],
            ["lost_reason_id"],
            ["expected_revenue:sum", "date_closed:max"])
        by_reason = {
            reason.id: (revenue, closed)
            for reason, revenue, closed in grouped}
        for reason in self:
            revenue, closed = by_reason.get(reason.id, (0.0, False))
            reason.oski_lost_revenue = revenue
            reason.oski_last_lost_on = closed.date() if closed else False

    def action_oski_open_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunités perdues — %s", self.name),
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("lost_reason_id", "=", self.id)],
            "context": {"active_test": False, "create": False},
        }
