from datetime import datetime

from .common import RentalCase


class TestPricing(RentalCase):

    def _price(self, asset, days=0, hours=0):
        start = datetime(2026, 8, 1, 8, 0)
        from datetime import timedelta
        return asset._get_rental_price(start, start + timedelta(days=days, hours=hours))

    def test_greedy_no_best_price(self):
        # 6 jours = 6 × 100 = 600 (glouton pur, pas d'optimisation semaine)
        asset = self._make_asset(price_day=100, price_week=500)
        self.assertEqual(self._price(asset, days=6), 600.0)

    def test_week_plus_days(self):
        asset = self._make_asset(price_day=100, price_week=500)
        self.assertEqual(self._price(asset, days=10), 800.0)

    def test_month_tier(self):
        asset = self._make_asset(price_day=100, price_week=500, price_month=1500)
        # 35 jours = 1 mois (30j) + 5 jours = 1500 + 500 = 2000
        self.assertEqual(self._price(asset, days=35), 2000.0)

    def test_zero_tier_skipped(self):
        # pas de tarif semaine → 10 jours = 10 × 100
        asset = self._make_asset(price_day=100, price_week=0)
        self.assertEqual(self._price(asset, days=10), 1000.0)

    def test_remainder_rounds_up_finest(self):
        # 1 jour + 3 h, palier le plus fin = jour → 2 jours
        asset = self._make_asset(price_day=100)
        self.assertEqual(self._price(asset, days=1, hours=3), 200.0)

    def test_hour_tier(self):
        asset = self._make_asset(price_hour=10, price_day=100)
        # 1 jour + 3 h = 100 + 30
        self.assertEqual(self._price(asset, days=1, hours=3), 130.0)

    def test_min_granularity_day_ignores_hours(self):
        asset = self._make_asset(price_hour=10, price_day=100)
        self.env['ir.config_parameter'].sudo().set_param(
            'oski_rental.min_granularity', 'day')
        # palier heure ignoré → 1 j + 3 h arrondi à 2 jours
        self.assertEqual(self._price(asset, days=1, hours=3), 200.0)

    def test_no_price_returns_zero(self):
        asset = self._make_asset(price_day=0, price_week=0)
        self.assertEqual(self._price(asset, days=3), 0.0)

    def test_negative_duration_zero(self):
        from datetime import datetime
        asset = self._make_asset(price_day=100)
        self.assertEqual(
            asset._get_rental_price(datetime(2026, 8, 2), datetime(2026, 8, 1)), 0.0)
