import calendar

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

    def _get_next_date(self, from_date, anchor=None):
        """Échéance suivant ``from_date``.

        Mois et années : le 31 donne le 28/29 février, mais le mois suivant
        doit revenir au jour d'origine (31 mars), pas rester au 28. On repart
        donc de ``anchor`` (date de début) quand ``from_date`` est sur sa
        grille d'échéances ; à défaut, une fin de mois reste une fin de mois.
        """
        self.ensure_one()
        step = relativedelta(**{_UNIT_KEY[self.billing_unit]: self.billing_interval})
        if self.billing_unit not in ("month", "year"):
            return from_date + step
        months = self.billing_interval * (12 if self.billing_unit == "year" else 1)
        if anchor and anchor <= from_date:
            elapsed = (from_date.year - anchor.year) * 12 + from_date.month - anchor.month
            periods = elapsed // months
            if anchor + relativedelta(months=periods * months) == from_date:
                return anchor + relativedelta(months=(periods + 1) * months)
        if from_date.day == calendar.monthrange(from_date.year, from_date.month)[1]:
            target = from_date + step
            return target.replace(
                day=calendar.monthrange(target.year, target.month)[1]
            )
        return from_date + step
