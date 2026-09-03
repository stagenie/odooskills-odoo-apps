from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2026-08-17">
      <Cube currency="USD" rate="1.1000"/>
      <Cube currency="GBP" rate="0.8500"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""

EMPTY_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube time="2026-08-17"/></Cube>
</gesmes:Envelope>
"""

COMPANY = "odoo.addons.oski_currency_rate_auto.models.res_company.ResCompany"


@tagged("post_install", "-at_install")
class TestCurrencyRateAuto(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eur = cls.env.ref("base.EUR")
        cls.usd = cls.env.ref("base.USD")
        cls.gbp = cls.env.ref("base.GBP")
        cls.chf = cls.env.ref("base.CHF")
        (cls.eur | cls.usd | cls.gbp).write({"active": True})
        cls.chf.active = False
        cls.company = cls.env["res.company"].create({
            "name": "Société en euro", "currency_id": cls.eur.id})
        cls.Rate = cls.env["res.currency.rate"]

    def _fetch(self, content=FEED):
        return patch.object(type(self.env["res.company"]),
                            "_oski_fetch_ecb_xml", lambda company: content)

    def _rate(self, currency, company=None):
        return self.Rate.search([
            ("currency_id", "=", currency.id),
            ("company_id", "=", (company or self.company).id),
            ("name", "=", fields.Date.to_date("2026-08-17"))], limit=1)

    # --- lecture de la source --------------------------------------------

    def test_the_feed_is_read_with_its_date(self):
        rate_date, rates = self.env["res.company"]._oski_parse_ecb_xml(FEED)
        self.assertEqual(rate_date, fields.Date.to_date("2026-08-17"))
        self.assertEqual(rates["USD"], 1.1)
        self.assertEqual(rates["GBP"], 0.85)

    def test_the_euro_is_the_pivot_and_is_added(self):
        """La BCE ne publie pas l'euro : il est le pivot. Sans lui à 1, une
        société en euro n'aurait aucun point de comparaison."""
        _date, rates = self.env["res.company"]._oski_parse_ecb_xml(FEED)
        self.assertEqual(rates["EUR"], 1.0)

    def test_an_empty_feed_is_refused(self):
        with self.assertRaises(UserError):
            self.env["res.company"]._oski_parse_ecb_xml(EMPTY_FEED)

    # --- écriture des taux ------------------------------------------------

    def test_rates_are_written_for_active_currencies(self):
        with self._fetch():
            self.company._oski_update_rates()
        self.assertAlmostEqual(self._rate(self.usd).company_rate, 1.1, places=6)
        self.assertAlmostEqual(self._rate(self.gbp).company_rate, 0.85, places=6)

    def test_an_inactive_currency_is_left_alone(self):
        with self._fetch():
            self.company._oski_update_rates()
        self.assertFalse(self._rate(self.chf))

    def test_the_company_currency_gets_no_rate_of_its_own(self):
        with self._fetch():
            self.company._oski_update_rates()
        self.assertFalse(self._rate(self.eur))

    def test_a_currency_absent_from_the_feed_is_skipped(self):
        self.chf.active = True
        with self._fetch():
            self.company._oski_update_rates()
        self.assertFalse(self._rate(self.chf))

    def test_the_company_currency_is_the_pivot_whatever_it_is(self):
        """Société en dollar : 1 USD vaut 0,85/1,10 GBP, et l'euro cesse d'être
        le repère."""
        usd_company = self.env["res.company"].create({
            "name": "Société en dollar", "currency_id": self.usd.id})
        with self._fetch():
            usd_company._oski_update_rates()
        self.assertAlmostEqual(
            self._rate(self.gbp, usd_company).company_rate, 0.85 / 1.1, places=6)
        self.assertAlmostEqual(
            self._rate(self.eur, usd_company).company_rate, 1 / 1.1, places=6)

    def test_a_second_run_the_same_day_updates_instead_of_duplicating(self):
        with self._fetch():
            self.company._oski_update_rates()
        first = self._rate(self.usd)
        with self._fetch(FEED.replace(b"1.1000", b"1.2000")):
            self.company._oski_update_rates()
        again = self._rate(self.usd)
        self.assertEqual(first, again, "un seul taux par devise et par jour")
        self.assertAlmostEqual(again.company_rate, 1.2, places=6)

    def test_a_success_clears_the_last_error(self):
        self.company.oski_rate_last_error = "panne précédente"
        with self._fetch():
            self.company._oski_update_rates()
        self.assertFalse(self.company.oski_rate_last_error)
        self.assertTrue(self.company.oski_rate_last_sync)

    # --- tâche planifiée --------------------------------------------------

    def test_the_cron_serves_only_those_who_asked(self):
        other = self.env["res.company"].create({
            "name": "Société sans taux", "currency_id": self.eur.id})
        self.company.oski_rate_auto = True
        with self._fetch():
            self.env["res.company"]._cron_update_currency_rates()
        self.assertTrue(self._rate(self.usd))
        self.assertFalse(self._rate(self.usd, other))

    def test_a_broken_company_does_not_stop_the_others(self):
        """L'erreur est inscrite sur la société : un message dans le journal du
        serveur ne se lit pas depuis l'interface."""
        broken = self.env["res.company"].create({
            "name": "Société en panne", "currency_id": self.eur.id,
            "oski_rate_auto": True})
        self.company.oski_rate_auto = True

        def fetch(company):
            if company.id == broken.id:
                raise ConnectionError("la BCE ne répond pas")
            return FEED

        with patch.object(type(self.env["res.company"]), "_oski_fetch_ecb_xml", fetch):
            self.env["res.company"]._cron_update_currency_rates()
        self.assertIn("BCE", broken.oski_rate_last_error)
        self.assertTrue(self._rate(self.usd), "l'autre société a bien été servie")

    def test_the_cron_sleeps_until_someone_asks(self):
        cron = self.env.ref("oski_currency_rate_auto.ir_cron_oski_currency_rate")
        self.env["res.company"].search([]).write({"oski_rate_auto": False})
        self.assertFalse(cron.active, "aucune base ne doit appeler la BCE sans consentement")
        self.company.oski_rate_auto = True
        self.assertTrue(cron.active)
        self.company.oski_rate_auto = False
        self.assertFalse(cron.active)
