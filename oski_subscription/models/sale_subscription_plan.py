from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_UNIT_KEY = {"day": "days", "week": "weeks", "month": "months", "year": "years"}


class SaleSubscriptionPlan(models.Model):
    _name = "sale.subscription.plan"
    _description = "Plan d'abonnement"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    billing_unit = fields.Selection(
        [("day", "Jour"), ("week", "Semaine"), ("month", "Mois"), ("year", "Année")],
        string="Unité de facturation",
        default="month",
        required=True,
    )
    billing_interval = fields.Integer(string="Intervalle", default=1, required=True)
    auto_post_invoice = fields.Boolean(
        string="Poster automatiquement la facture", default=False
    )
    active = fields.Boolean(default=True)

    @api.constrains("billing_interval")
    def _check_interval(self):
        for plan in self:
            if plan.billing_interval < 1:
                raise ValidationError("L'intervalle de facturation doit être >= 1.")

    def _get_next_date(self, from_date):
        self.ensure_one()
        return from_date + relativedelta(
            **{_UNIT_KEY[self.billing_unit]: self.billing_interval}
        )
