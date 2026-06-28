import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

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

    def _prepare_invoice_line_vals(self, line):
        return {
            "product_id": line.product_id.id,
            "name": line.name or line.product_id.display_name,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "tax_ids": [fields.Command.set(line.tax_ids.ids)],
        }

    def _prepare_invoice_vals(self):
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": fields.Date.today(),
            "invoice_origin": self.name,
            "company_id": self.company_id.id,
            "invoice_line_ids": [
                fields.Command.create(self._prepare_invoice_line_vals(line))
                for line in self.line_ids
            ],
        }

    def _generate_invoice(self):
        self.ensure_one()
        move = self.env["account.move"].create(self._prepare_invoice_vals())
        if self.plan_id.auto_post_invoice:
            move.action_post()
        self.invoice_ids = [fields.Command.link(move.id)]
        self.next_invoice_date = self.plan_id._get_next_date(self.next_invoice_date)
        if self.date_end and self.next_invoice_date > self.date_end:
            self.action_close()
        self.message_post(body="Facture générée : %s" % (move.name or move.id))
        return move

    def action_generate_invoice(self):
        self.ensure_one()
        self._generate_invoice()
        return self.action_view_invoices()

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Factures",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
        }

    @api.model
    def _cron_generate_invoices(self):
        today = fields.Date.today()
        subs = self.search(
            [("state", "=", "progress"), ("next_invoice_date", "<=", today)]
        )
        for sub in subs:
            try:
                sub._generate_invoice()
            except Exception:
                _logger.exception(
                    "Échec génération facture abonnement %s", sub.id
                )
