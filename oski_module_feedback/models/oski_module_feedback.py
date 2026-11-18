from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_MAX_PER_DAY = 5


class OskiModuleFeedback(models.Model):
    """Demande d'évolution d'un client sur un module payant du store.

    Bug, modification, amélioration ou autre : le propriétaire du store
    trie et analyse chaque demande ; le demandeur suit le statut dans son
    espace client.
    """

    _name = "oski.module.feedback"
    _description = "Module change request"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default="New",
    )
    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, index=True,
        ondelete="cascade", tracking=True,
    )
    is_pack = fields.Boolean(
        string="Pack", compute="_compute_is_pack", store=True,
        help="The module is a suite that installs several modules.",
    )
    odoo_version_id = fields.Many2one("oski.odoo.version", string="Odoo version")
    request_type = fields.Selection(
        [
            ("bug", "Bug"),
            ("change", "Change request"),
            ("improvement", "Improvement"),
            ("other", "Other"),
        ],
        string="Type", required=True, default="improvement", tracking=True,
    )
    title = fields.Char(string="Title", required=True, tracking=True)
    description = fields.Text(string="Description", required=True)
    steps = fields.Text(string="Steps to reproduce")
    attachment_ids = fields.Many2many(
        "ir.attachment", "oski_module_feedback_attachment_rel",
        "feedback_id", "attachment_id", string="Attachments",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Requester", required=True, index=True, tracking=True,
    )
    source = fields.Selection(
        [("module_page", "Module page"), ("trial", "1-hour trial")],
        string="Source", default="module_page", required=True,
    )
    trial_id = fields.Many2one("oski.module.trial", string="Trial", ondelete="set null")
    state = fields.Selection(
        [
            ("new", "New"),
            ("analysis", "Under review"),
            ("planned", "Planned"),
            ("done", "Delivered"),
            ("rejected", "Declined"),
        ],
        string="Status", default="new", required=True, tracking=True,
        group_expand="_group_expand_state",
    )
    released_version = fields.Char(
        string="Delivered in version", tracking=True,
        help="Module version that ships the change, e.g. 19.0.1.2.0.",
    )
    decision_note = fields.Text(
        string="Answer to the customer",
        help="Shown to the customer in their portal: what is planned, or why it is declined.",
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "High"), ("2", "Urgent")],
        string="Priority", default="0",
    )
    user_id = fields.Many2one(
        "res.users", string="Assigned to", tracking=True,
        domain="[('share', '=', False)]",
    )

    @api.depends("module_id.technical_name")
    def _compute_is_pack(self):
        for rec in self:
            rec.is_pack = (rec.module_id.technical_name or "").endswith("_suite")

    @api.model
    def _group_expand_state(self, states, domain):
        return [key for key, _label in type(self).state.selection]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = "/my/module-requests/%s" % rec.id

    @api.constrains("state", "released_version")
    def _check_released_version(self):
        for rec in self:
            if rec.state == "done" and not (rec.released_version or "").strip():
                raise ValidationError(_(
                    "Enter the module version that delivers request %s before marking it delivered.",
                    rec.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"].sudo()
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = sequence.next_by_code("oski.module.feedback") or "New"
        records = super().create(vals_list)
        for rec in records:
            rec.message_subscribe(partner_ids=rec.partner_id.ids)
        return records

    @api.model
    def _max_per_day(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "oski_module_feedback.max_per_day"
        )
        try:
            value = int(raw or 0)
        except ValueError:
            value = 0
        return value if value > 0 else DEFAULT_MAX_PER_DAY

    @api.model
    def _count_last_24h(self, partner):
        since = fields.Datetime.now() - timedelta(hours=24)
        return self.sudo().search_count([
            ("partner_id", "=", partner.id), ("create_date", ">=", since),
        ])

    # Boutons de la barre d'états
    def action_set_analysis(self):
        self.write({"state": "analysis"})

    def action_set_planned(self):
        self.write({"state": "planned"})

    def action_set_done(self):
        self.write({"state": "done"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_reset_new(self):
        self.write({"state": "new"})

    def _send_new_notifications(self):
        """Accusé au demandeur + notification à l'équipe (file d'envoi)."""
        ack = self.env.ref("oski_module_feedback.mail_template_feedback_ack", raise_if_not_found=False)
        new = self.env.ref("oski_module_feedback.mail_template_feedback_new", raise_if_not_found=False)
        for rec in self:
            if ack:
                ack.sudo().send_mail(rec.id, force_send=False)
            if new and new.sudo().email_to:
                new.sudo().send_mail(rec.id, force_send=False)
