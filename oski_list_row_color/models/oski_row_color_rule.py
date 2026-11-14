from xml.sax.saxutils import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OskiRowColorRule(models.Model):
    _name = "oski.row.color.rule"
    _description = "List Row Color Rule"
    _order = "model_id, sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade",
        help="Model whose list rows will be colored.",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Technical Name")
    decoration = fields.Selection(
        [
            ("info", "Blue (info)"),
            ("success", "Green (success)"),
            ("warning", "Orange (warning)"),
            ("danger", "Red (danger)"),
            ("muted", "Grey (muted)"),
            ("primary", "Primary"),
        ],
        string="Color", required=True, default="info",
    )
    expression = fields.Char(
        string="Condition", required=True,
        help="Python expression evaluated for each row, e.g. state == 'done' or amount_total > 1000.",
    )
    view_id = fields.Many2one(
        "ir.ui.view", string="Generated View", readonly=True, ondelete="set null",
    )

    def _get_base_list_view(self):
        self.ensure_one()
        return self.env["ir.ui.view"].search(
            [
                ("model", "=", self.model_name),
                ("type", "=", "list"),
                ("mode", "=", "primary"),
                ("inherit_id", "=", False),
            ],
            limit=1, order="priority,id",
        )

    def _build_arch(self):
        self.ensure_one()
        return (
            '<data><xpath expr="//list" position="attributes">'
            '<attribute name="decoration-%s">%s</attribute>'
            "</xpath></data>"
        ) % (self.decoration, escape(self.expression or ""))

    def _sync_view(self):
        for rule in self:
            base_view = rule._get_base_list_view()
            if not base_view:
                raise UserError(_(
                    "No primary list view found for model “%s”.",
                    rule.model_name or "",
                ))
            vals = {
                "name": "oski.row.color.%s.%s" % (rule.model_name, rule.id),
                "model": rule.model_name,
                "inherit_id": base_view.id,
                "mode": "extension",
                "priority": 99,
                "arch": rule._build_arch(),
                "active": rule.active,
            }
            if rule.view_id:
                rule.view_id.write(vals)
            else:
                rule.view_id = self.env["ir.ui.view"].create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._sync_view()
        return rules

    def write(self, vals):
        res = super().write(vals)
        watched = {"model_id", "decoration", "expression", "active"}
        if watched & set(vals):
            self._sync_view()
        return res

    def unlink(self):
        self.view_id.unlink()
        return super().unlink()
