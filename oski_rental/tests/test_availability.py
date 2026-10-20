from datetime import datetime

from odoo.exceptions import ValidationError

from .common import RentalCase


class TestAvailability(RentalCase):

    def test_unavailability_blocks(self):
        asset = self._make_asset()
        self.env['oski.rental.unavailability'].create({
            'asset_id': asset.id,
            'date_start': datetime(2026, 8, 10),
            'date_end': datetime(2026, 8, 15),
            'reason': 'maintenance',
        })
        self.assertFalse(asset.check_availability(
            datetime(2026, 8, 12), datetime(2026, 8, 13)))
        # bords exclusifs : finir pile au début d'une indispo = OK
        self.assertTrue(asset.check_availability(
            datetime(2026, 8, 8), datetime(2026, 8, 10)))
        self.assertTrue(asset.check_availability(
            datetime(2026, 8, 15), datetime(2026, 8, 16)))

    def test_unavailability_dates_check(self):
        asset = self._make_asset()
        with self.assertRaises(ValidationError):
            self.env['oski.rental.unavailability'].create({
                'asset_id': asset.id,
                'date_start': datetime(2026, 8, 15),
                'date_end': datetime(2026, 8, 10),
                'reason': 'other',
            })

    def test_available_when_nothing(self):
        asset = self._make_asset()
        self.assertTrue(asset.check_availability(
            datetime(2026, 8, 1), datetime(2026, 8, 2)))
