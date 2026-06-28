from odoo import api, fields, models
from odoo.exceptions import ValidationError

# facteur de normalisation mensuelle par unité, pour intervalle 1
_MRR_FACTOR = {
    "day": 30.0,
    "week": 30.0 / 7.0,
    "month": 1.0,
    "year": 1.0 / 12.0,
}


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _description = "Abonnement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Référence", default="New", copy=False, tracking=True)
    partner_id = fields.Many2one(
        "res.partner", string="Client", required=True, tracking=True
    )
    plan_id = fields.Many2one(
        "sale.subscription.plan", string="Plan", required=True, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", string="Société", required=True, default=lambda s: s.env.company
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Devise", store=True
    )
    pricelist_id = fields.Many2one("product.pricelist", string="Liste de prix")
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("progress", "En cours"),
            ("paused", "Suspendu"),
            ("closed", "Résilié"),
        ],
        string="État",
        default="draft",
        tracking=True,
    )
    date_start = fields.Date(string="Début")
    date_end = fields.Date(string="Fin d'engagement")
    next_invoice_date = fields.Date(string="Prochaine facture")
    date_closed = fields.Date(string="Résilié le")
    line_ids = fields.One2many(
        "sale.subscription.line", "subscription_id", string="Lignes"
    )
    invoice_ids = fields.Many2many(
        "account.move", string="Factures", copy=False
    )
    invoice_count = fields.Integer(
        string="Nb factures", compute="_compute_invoice_count"
    )
    recurring_total = fields.Monetary(
        string="Total récurrent", compute="_compute_recurring_total", store=True
    )
    mrr = fields.Monetary(
        string="MRR", compute="_compute_mrr", store=True,
        help="Revenu mensuel récurrent normalisé.",
    )

    @api.depends("line_ids.price_subtotal")
    def _compute_recurring_total(self):
        for sub in self:
            sub.recurring_total = sum(sub.line_ids.mapped("price_subtotal"))

    @api.depends("recurring_total", "plan_id.billing_unit", "plan_id.billing_interval")
    def _compute_mrr(self):
        for sub in self:
            plan = sub.plan_id
            if not plan or not plan.billing_interval:
                sub.mrr = 0.0
                continue
            sub.mrr = sub.recurring_total * _MRR_FACTOR[plan.billing_unit] / plan.billing_interval

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for sub in self:
            if sub.date_start and sub.date_end and sub.date_end < sub.date_start:
                raise ValidationError(
                    "La fin d'engagement ne peut précéder le début."
                )

    def action_start(self):
        for sub in self:
            if sub.name in (False, "New"):
                sub.name = (
                    self.env["ir.sequence"]
                    .sudo()
                    .next_by_code("sale.subscription")
                    or "New"
                )
            sub.state = "progress"
            sub.date_start = fields.Date.today()
            sub.next_invoice_date = fields.Date.today()

    def action_pause(self):
        self.write({"state": "paused"})

    def action_resume(self):
        today = fields.Date.today()
        for sub in self:
            sub.state = "progress"
            if sub.next_invoice_date and sub.next_invoice_date < today:
                sub.next_invoice_date = today

    def action_close(self):
        self.write({"state": "closed", "date_closed": fields.Date.today()})
