from odoo import api, fields, models


class OskiDevRequest(models.Model):
    _name = "oski.dev.request"
    _description = "Module development request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda self: "New",
    )
    # Requester
    requester_name = fields.Char(string="Name", required=True, tracking=True)
    company_name = fields.Char(string="Company")
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Phone")
    user_id = fields.Many2one(
        "res.users", string="Requester", readonly=True,
        default=lambda self: self.env.user,
    )
    # Need
    subject = fields.Char(string="Subject", required=True, tracking=True)
    description = fields.Text(string="Description of the need", required=True)
    category_id = fields.Many2one("oski.module.category", string="Category")
    # The oski.odoo.version reference table is authoritative: adding an Odoo
    # version stays a plain record, without touching the code (order = most
    # recent first, upcoming version included).
    odoo_version = fields.Selection(
        selection="_selection_odoo_version",
        string="Target Odoo version",
        default=lambda self: self.env["oski.odoo.version"].get_default(),
    )

    @api.model
    def _selection_odoo_version(self):
        return [(v, v) for v in self.env["oski.odoo.version"].get_supported()]
    budget_range = fields.Selection(
        [
            ("lt_500", "Under €500"),
            ("b_500_1500", "€500 – €1,500"),
            ("b_1500_5000", "€1,500 – €5,000"),
            ("gt_5000", "Over €5,000"),
            ("to_discuss", "To discuss"),
        ],
        string="Budget",
        required=True,
        default="to_discuss",
    )
    delivery_mode = fields.Selection(
        [
            ("store", "Published on the store (standard price)"),
            ("exclusive", "Exclusive to me (significantly higher price)"),
        ],
        string="Delivery mode",
        required=True,
        default="store",
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Attachments",
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("analysis", "Under review"),
            ("quoted", "Quote sent"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("delivered", "Delivered"),
        ],
        string="Status",
        default="new",
        tracking=True,
        group_expand="_group_expand_state",
    )
    assigned_id = fields.Many2one(
        "res.users", string="Assigned to", tracking=True,
        domain="[('share', '=', False)]",
    )
    module_id = fields.Many2one(
        "oski.module", string="Delivered module",
        help="Store module created in response to this request.",
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "High"), ("2", "Urgent")],
        string="Priority", default="0",
    )

    @api.model
    def _group_expand_state(self, states, domain):
        return [s[0] for s in type(self).state.selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = self.env["ir.sequence"].sudo().next_by_code(
                    "oski.dev.request"
                ) or "New"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State transitions (header buttons)
    # ------------------------------------------------------------------
    def action_set_analysis(self):
        self.write({"state": "analysis"})

    def action_set_quoted(self):
        self.write({"state": "quoted"})

    def action_accept(self):
        self.write({"state": "accepted"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_set_delivered(self):
        self.write({"state": "delivered"})
