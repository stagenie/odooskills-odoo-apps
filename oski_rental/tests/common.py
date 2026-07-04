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

    @classmethod
    def _make_order(cls, assets, date_start, date_end, **kw):
        vals = {
            'partner_id': cls.partner.id,
            'date_start': date_start,
            'date_end': date_end,
            'line_ids': [(0, 0, {
                'asset_id': asset.id,
                'date_start': date_start,
                'date_end': date_end,
            }) for asset in assets],
        }
        vals.update(kw)
        return cls.env['oski.rental.order'].create(vals)
