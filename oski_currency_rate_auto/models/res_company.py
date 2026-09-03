import logging
from xml.etree import ElementTree

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
TIMEOUT = 20
CRON_XMLID = "oski_currency_rate_auto.ir_cron_oski_currency_rate"


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_rate_auto = fields.Boolean(
        string="Taux de change automatiques",
        help="Une tâche planifiée quotidienne inscrit les taux publiés par la "
             "Banque centrale européenne.")
    oski_rate_provider = fields.Selection(
        [("ecb", "Banque centrale européenne")],
        string="Source des taux", default="ecb", required=True)
    oski_rate_last_sync = fields.Datetime(string="Dernière mise à jour", readonly=True)
    oski_rate_last_error = fields.Char(string="Dernière erreur", readonly=True)

    # --- interrupteur -----------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        self._oski_sync_cron_state()
        return companies

    def write(self, vals):
        result = super().write(vals)
        if "oski_rate_auto" in vals:
            self._oski_sync_cron_state()
        return result

    @api.model
    def _oski_sync_cron_state(self):
        """La tâche ne tourne que si quelqu'un l'a demandée.

        Sans cela le serveur appellerait la BCE chaque nuit sur toute base où
        le module est simplement installé.
        """
        cron = self.env.ref(CRON_XMLID, raise_if_not_found=False)
        if not cron:
            return
        wanted = bool(self.sudo().search_count([("oski_rate_auto", "=", True)]))
        if cron.sudo().active != wanted:
            cron.sudo().active = wanted

    # --- source -----------------------------------------------------------

    def _oski_fetch_ecb_xml(self):
        """Le seul point qui touche au réseau, isolé pour être remplaçable."""
        response = requests.get(ECB_URL, timeout=TIMEOUT)
        response.raise_for_status()
        return response.content

    @api.model
    def _oski_parse_ecb_xml(self, content):
        """Rend ``(date, {code: taux pour 1 EUR})``.

        L'euro ne figure pas dans le flux — il en est le pivot — et y est
        ajouté à 1, sans quoi une société en euro n'aurait aucun point de
        comparaison.
        """
        root = ElementTree.fromstring(content)
        rates = {"EUR": 1.0}
        rate_date = False
        for node in root.iter():
            if "time" in node.attrib:
                rate_date = fields.Date.to_date(node.attrib["time"])
            currency = node.attrib.get("currency")
            if currency:
                try:
                    rates[currency] = float(node.attrib["rate"])
                except (KeyError, ValueError):
                    continue
        if len(rates) == 1:
            raise UserError(_("La source n'a rendu aucun taux exploitable."))
        return rate_date or fields.Date.context_today(self), rates

    # --- écriture ---------------------------------------------------------

    def _oski_apply_rates(self, rate_date, rates):
        """Inscrit les taux pour cette société, sa devise servant de pivot.

        ``company_rate`` — et non ``rate`` — parce que c'est le taux tel qu'un
        comptable le lit : combien d'unités de la devise pour une unité de la
        devise de la société. Odoo fait lui-même la conversion interne.
        """
        self.ensure_one()
        pivot = rates.get(self.currency_id.name)
        if not pivot:
            raise UserError(_(
                "La source ne publie pas de taux pour %s, la devise de la société.",
                self.currency_id.name))
        Rate = self.env["res.currency.rate"].sudo()
        currencies = self.env["res.currency"].search([
            ("active", "=", True), ("id", "!=", self.currency_id.id)])
        written = Rate.browse()
        for currency in currencies:
            value = rates.get(currency.name)
            if not value:
                continue
            existing = Rate.search([
                ("currency_id", "=", currency.id),
                ("company_id", "=", self.id),
                ("name", "=", rate_date)], limit=1)
            if existing:
                existing.company_rate = value / pivot
                written |= existing
            else:
                written |= Rate.create({
                    "currency_id": currency.id,
                    "company_id": self.id,
                    "name": rate_date,
                    "company_rate": value / pivot,
                })
        return written

    def _oski_update_rates(self):
        """Met à jour une société et rend les taux écrits."""
        self.ensure_one()
        rate_date, rates = self._oski_parse_ecb_xml(self._oski_fetch_ecb_xml())
        written = self._oski_apply_rates(rate_date, rates)
        self.sudo().write({
            "oski_rate_last_sync": fields.Datetime.now(),
            "oski_rate_last_error": False,
        })
        return written

    def action_oski_update_rates(self):
        self.ensure_one()
        written = self._oski_update_rates()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("%s taux mis à jour.", len(written)),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    @api.model
    def _cron_update_currency_rates(self):
        """Une société en panne n'empêche pas les autres d'être servies.

        L'erreur est inscrite sur la société — un message dans le journal du
        serveur ne se lit pas depuis l'interface.
        """
        companies = self.sudo().search([("oski_rate_auto", "=", True)])
        for company in companies:
            try:
                company._oski_update_rates()
            except Exception as error:  # noqa: BLE001 - une panne n'arrête pas la file
                _logger.exception("Taux de change : mise à jour impossible pour %s",
                                  company.display_name)
                company.write({"oski_rate_last_error": str(error)[:250]})
        return True
