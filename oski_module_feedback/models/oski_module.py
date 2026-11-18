from odoo import api, fields, models


class OskiModule(models.Model):
    _inherit = "oski.module"

    feedback_ids = fields.One2many(
        "oski.module.feedback", "module_id", string="Change requests",
    )
    feedback_count = fields.Integer(
        string="Change requests", compute="_compute_feedback_count",
    )

    @api.depends("feedback_ids")
    def _compute_feedback_count(self):
        groups = self.env["oski.module.feedback"].sudo()._read_group(
            [("module_id", "in", self.ids)], ["module_id"], ["__count"],
        )
        counts = {module.id: count for module, count in groups}
        for module in self:
            module.feedback_count = counts.get(module.id, 0)

    def action_view_feedback(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "oski_module_feedback.action_oski_module_feedback"
        )
        action["domain"] = [("module_id", "=", self.id)]
        action["context"] = {"default_module_id": self.id}
        return action
