from odoo.tests.common import TransactionCase


class RentalCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Client Location Test'})

    @classmethod
    def _make_asset(cls, name='Asset Test', **kw):
        vals = {
            'name': name,
            'price_hour': 0.0,
            'price_day': 100.0,
            'price_week': 500.0,
            'price_month': 0.0,
            'deposit_amount': 0.0,
        }
        vals.update(kw)
        return cls.env['oski.rental.asset'].create(vals)
