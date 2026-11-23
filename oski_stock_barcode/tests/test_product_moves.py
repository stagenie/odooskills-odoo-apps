from odoo.tests.common import HttpCase, tagged
import json


@tagged('post_install', '-at_install')
class TestProductMoves(HttpCase):

    def test_recent_moves(self):
        product = self.env['product.product'].create({
            'name': 'Mv', 'is_storable': True})
        stock = self.env.ref('stock.stock_location_stock')
        supplier = self.env.ref('stock.stock_location_suppliers')
        # two done receipts
        for i in range(2):
            move = self.env['stock.move'].create({
                'product_id': product.id, 'product_uom_qty': 1,
                'uom_id': product.uom_id.id,
                'location_id': supplier.id, 'location_dest_id': stock.id})
            move._action_confirm()
            move.quantity = 1
            move.picked = True
            move._action_done()
        # force distinct done-dates to verify order='date desc'
        lines = self.env['stock.move.line'].search(
            [('product_id', '=', product.id), ('state', '=', 'done')])
        self.assertGreaterEqual(len(lines), 2)
        # Odoo 20 : stock.move.line.date = related stocké de move_id.date
        # (stock/models/stock_move_line.py:61) → vider l'ORM AVANT l'UPDATE,
        # sinon le recalcul en attente écrase la date forcée ; dater aussi le
        # mouvement pour rester cohérent avec le related.
        self.env.flush_all()
        for line, date in ((lines[0], '2026-01-01 08:00:00'),
                           (lines[1], '2026-06-01 08:00:00')):
            self.env.cr.execute(
                "UPDATE stock_move_line SET date = %s WHERE id = %s",
                (date, line.id))
            self.env.cr.execute(
                "UPDATE stock_move SET date = %s WHERE id = %s",
                (date, line.move_id.id))
        self.env.invalidate_all()

        # L'opérateur lit l'heure dans son fuseau, au format de sa langue.
        self.env.ref('base.user_admin').write({'tz': 'Europe/Paris', 'lang': 'en_US'})
        self.authenticate('admin', 'admin')
        r = self.url_open('/oski_stock_barcode/get_product_moves',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                'params': {'product_id': product.id}}).encode(),
            headers={'Content-Type': 'application/json'})
        res = json.loads(r.content)['result']
        self.assertGreaterEqual(len(res['moves']), 2)
        self.assertIn('quantity', res['moves'][0])
        # 08:00 UTC le 1er juin = 10:00 à Paris (heure d'été), format de la langue en_US
        self.assertRegex(res['moves'][0]['date'], r'^0?6/0?1/(20)?26')
        self.assertIn('10:00', res['moves'][0]['date'])
