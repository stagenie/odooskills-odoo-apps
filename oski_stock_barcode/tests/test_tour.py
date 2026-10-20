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
                'product_id': product.id, 'product_uom_qty': 2,
                'uom_id': product.uom_id.id,
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

    def test_delivery_in_checked_company(self):
        """Opérateur A + B, seule B cochée dans le sélecteur (cookie ``cids``) :
        l'écran ne propose que le bon de B et le valide (avant : bons de A
        aussi listés, le JS n'envoyait pas les sociétés cochées)."""
        company_a = self.env.ref('base.main_company')
        company_b = self.env['res.company'].create({'name': 'Société B tour'})
        customers = self.env.ref('stock.stock_location_customers')
        product = self.env['product.product'].create({
            'name': 'Article tour société', 'is_storable': True,
            'barcode': 'OSKITOURCO', 'company_id': False})
        pickings = {}
        for company, origin in ((company_a, 'OSKI-CO-A'), (company_b, 'OSKI-CO-B')):
            wh = self.env['stock.warehouse'].search(
                [('company_id', '=', company.id)], limit=1)
            self.env['stock.quant']._update_available_quantity(
                product, wh.lot_stock_id, 1)
            picking = self.env['stock.picking'].with_company(company).create({
                'picking_type_id': wh.out_type_id.id,
                'location_id': wh.lot_stock_id.id,
                'location_dest_id': customers.id,
                'company_id': company.id, 'origin': origin,
                'move_ids': [(0, 0, {
                    'product_id': product.id, 'product_uom_qty': 1,
                    'uom_id': product.uom_id.id,
                    'location_id': wh.lot_stock_id.id,
                    'location_dest_id': customers.id,
                    'company_id': company.id})],
            })
            picking.action_confirm()
            picking.action_assign()
            pickings[company] = picking
        new_test_user(self.env, login='oski_tour_mc', password='oski_tour_mc',
                      groups='stock.group_stock_user',
                      company_id=company_a.id,
                      company_ids=[(6, 0, (company_a | company_b).ids)])
        action = self.env.ref('oski_stock_barcode.action_barcode_operations')
        self.start_tour(f'/odoo/action-{action.id}',
                        'oski_stock_barcode_company_tour',
                        login='oski_tour_mc',
                        cookies={'cids': str(company_b.id)})
        self.assertEqual(pickings[company_b].state, 'done')
        self.assertEqual(pickings[company_a].state, 'assigned')
