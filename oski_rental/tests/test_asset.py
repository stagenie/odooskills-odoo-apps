from .common import RentalCase


class TestAsset(RentalCase):

    def test_code_sequence(self):
        asset = self._make_asset()
        self.assertTrue(asset.code.startswith('OSKA/'))

    def test_code_unique(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        a1 = self._make_asset()
        with mute_logger('odoo.sql_db'), \
                self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._make_asset(code=a1.code)
            self.env.flush_all()

    def test_default_product_exists(self):
        product = self.env.ref('oski_rental.product_rental_default')
        self.assertEqual(product.type, 'service')

    def test_category(self):
        cat = self.env['oski.rental.category'].create({'name': 'Véhicules'})
        asset = self._make_asset(category_id=cat.id)
        self.assertEqual(asset.category_id, cat)
