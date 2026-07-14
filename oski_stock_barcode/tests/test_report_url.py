from odoo.tests.common import HttpCase, tagged
import json


@tagged('post_install', '-at_install')
class TestReportUrl(HttpCase):

    def test_delivery_report_url_renders(self):
        product = self.env['product.product'].create({
            'name': 'PP', 'is_storable': True})
        ptype = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': ptype.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        self.authenticate('admin', 'admin')
        r = self.url_open('/oski_stock_barcode/get_report_url',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                'params': {'picking_id': picking.id}}).encode(),
            headers={'Content-Type': 'application/json'})
        res = json.loads(r.content)['result']
        self.assertIn('/report/pdf/', res['url'])
        pdf = self.url_open(res['url'])
        self.assertEqual(pdf.status_code, 200)
