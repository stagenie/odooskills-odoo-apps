import logging

from markupsafe import Markup

from odoo import api, fields, models
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

LIVE_STATES = ("draft", "sent")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    oski_expired_on = fields.Date(
        string="Expired On", readonly=True, copy=False,
        help="Date on which the scheduled action cancelled this expired quotation.")
    oski_reminder_sent_on = fields.Date(
        string="Reminder Sent On", readonly=True, copy=False)

    # -- Tâche planifiée --------------------------------------------------

    @api.model
    def _oski_cron_expire_quotations(self):
        """Relance d'abord, péremption ensuite.

        L'ordre compte : un devis relancé le matin puis annulé la nuit même
        ferait passer le vendeur pour un menteur auprès de son client.
        """
        today = fields.Date.context_today(self)
        for company in self.env["res.company"].search([]):
            orders = self.with_company(company).search([
                ("company_id", "=", company.id),
                ("state", "in", LIVE_STATES),
                ("validity_date", "!=", False),
            ])
            orders._oski_remind(company, today)
            orders._oski_expire(company, today)
        return True

    def _oski_remind(self, company, today):
        days = company.oski_quote_reminder_days
        if days <= 0:
            return self.browse()
        limit = fields.Date.add(today, days=days)
        # Une seule relance par échéance : sans ce garde-fou, la tâche
        # quotidienne empilerait une activité par jour de la fenêtre. Une
        # relance antérieure à la fenêtre (échéance repoussée depuis) ne
        # compte plus.
        due = self.filtered(
            lambda order: order.validity_date and today <= order.validity_date <= limit
            and not (order.oski_reminder_sent_on and order.oski_reminder_sent_on
                     >= fields.Date.subtract(order.validity_date, days=days))
            and not order.oski_expired_on)
        for order in due:
            order._oski_notify_salesperson()
        due.write({"oski_reminder_sent_on": today})
        return due

    def _oski_expire(self, company, today):
        if not company.oski_quote_expire_active:
            return self.browse()
        stale = self.filtered(
            lambda order: order.validity_date and order.validity_date < today
            and not order.locked)
        for order in stale:
            # Le journal du devis doit dire QUI l'a annulé et pourquoi : sans
            # cette trace, une annulation nocturne passe pour une manipulation.
            order.message_post(
                body=Markup("<p>%s</p>") % order._oski_reader_env()._(
                    "Quotation expired on %(date)s: its expiration date "
                    "had passed.", date=format_date(order._oski_reader_env(), order.validity_date)),
                subtype_xmlid="mail.mt_note")
        if stale:
            stale._action_cancel()
            stale.write({"oski_expired_on": today})
        return stale

    def _oski_reader_env(self):
        """L'environnement dans la langue du vendeur, qui lit la trace.

        La tâche planifiée tourne sans langue : sans cela, la note et
        l'activité seraient écrites en anglais pour tous.
        """
        self.ensure_one()
        user = self.user_id or self.create_uid
        return self.with_context(lang=user.lang or self.env.lang).env

    def _oski_notify_salesperson(self):
        """Une activité, jamais un courriel.

        Le vendeur vit dans Odoo ; une activité se retrouve dans sa liste du
        jour, là où un courriel de plus se perd.
        """
        self.ensure_one()
        user = self.user_id or self.create_uid
        if not user or not user.active:
            return
        reader = self._oski_reader_env()
        self.env["mail.activity"].sudo().with_context(
            mail_activity_quick_update=True).create({
                "res_model_id": self.env["ir.model"]._get_id("sale.order"),
                "res_id": self.id,
                "activity_type_id": self.env.ref(
                    "mail.mail_activity_data_todo").id,
                "user_id": user.id,
                "date_deadline": self.validity_date,
                "summary": reader._("Follow up on the quotation before it expires"),
                "note": Markup("<p>%s</p>") % reader._(
                    "This quotation expires on %(date)s.", date=format_date(reader, self.validity_date)),
            })
