from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestBarcodeTour(HttpCase):

    def test_delivery_scan_to_validation(self):
        """Parcours réel de l'écran : accueil → Expédition → bon → deux scans
        douchette → validation. Le stock est entièrement réservé par le bon."""
        stock = self.env.ref('stock.stock_location_stock')
        customers = self.env.ref('stock.stock_location_customers')
        product = self.env['product.product'].create({
            'name': 'Article tour', 'is_storable': True,
            'barcode': 'OSKITOUR01'})
        self.env['stock.quant']._update_available_quantity(product, stock, 2)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': stock.id, 'location_dest_id': customers.id,
            'origin': 'OSKI-TOUR',
            'move_ids': [(0, 0, {
                'name': 'oski barcode',
                'product_id': product.id, 'product_uom_qty': 2,
                'product_uom': product.uom_id.id,
                'location_id': stock.id, 'location_dest_id': customers.id})],
        })
        picking.action_confirm()
        picking.action_assign()
        new_test_user(self.env, login='oski_tour_op', password='oski_tour_op',
                      groups='stock.group_stock_user')
        action = self.env.ref('oski_stock_barcode.action_barcode_operations')
        self.start_tour(f'/odoo/action-{action.id}',
                        'oski_stock_barcode_delivery_tour',
                        login='oski_tour_op')
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.move_ids.quantity, 2)
