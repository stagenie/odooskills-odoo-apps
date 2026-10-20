import json

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestControllerGuards(HttpCase):
    """Garde-fous serveur des routes appelées par l'écran code-barres :
    stock réservé, idempotence de la validation, quantités invalides,
    emplacements ambigus, cloisonnement multi-société."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock = cls.env.ref('stock.stock_location_stock')
        cls.customers = cls.env.ref('stock.stock_location_customers')
        cls.product = cls.env['product.product'].create({
            'name': 'Article garde', 'is_storable': True,
            'barcode': 'OSKIGUARD01'})
        cls.env['stock.quant']._update_available_quantity(
            cls.product, cls.stock, 4)
        cls.out_type = cls.env.ref('stock.picking_type_out')
        cls.operator = new_test_user(
            cls.env, login='oski_bc_op', password='oski_bc_op',
            groups='stock.group_stock_user')

    def _delivery(self, qty=4):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.out_type.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customers.id,
            'move_ids': [(0, 0, {
                'name': 'oski barcode',
                'product_id': self.product.id, 'product_uom_qty': qty,
                'product_uom': self.product.uom_id.id,
                'location_id': self.stock.id,
                'location_dest_id': self.customers.id})],
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, 'assigned')
        return picking

    def _call(self, route, **params):
        r = self.url_open(
            f'/oski_stock_barcode/{route}',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                             'params': params}).encode(),
            headers={'Content-Type': 'application/json'})
        payload = json.loads(r.content)
        self.assertNotIn('error', payload, payload.get('error'))
        return payload['result']

    def test_reserved_stock_counts_for_its_own_delivery(self):
        """Tout le stock est réservé par CETTE livraison : l'écran doit
        l'afficher disponible et accepter le scan (avant : 0 disponible,
        scan refusé « stock insuffisant »)."""
        picking = self._delivery(4)
        self.authenticate('oski_bc_op', 'oski_bc_op')
        lines = self._call('get_picking_lines', picking_id=picking.id)['lines']
        self.assertEqual(lines[0]['available_qty'], 4)
        # Réservé n'est pas scanné : rien n'est compté avant le premier scan.
        self.assertEqual(lines[0]['done_qty'], 0)
        res = self._call('update_line_qty', picking_id=picking.id,
                         product_id=self.product.id, qty=4)
        self.assertTrue(res.get('success'), res)
        res = self._call('validate_picking', picking_id=picking.id)
        self.assertTrue(res.get('success'), res)
        self.assertEqual(picking.state, 'done')

    def test_validate_twice_is_refused(self):
        picking = self._delivery(4)
        self.authenticate('oski_bc_op', 'oski_bc_op')
        self._call('update_line_qty', picking_id=picking.id,
                   product_id=self.product.id, qty=4)
        self.assertTrue(self._call('validate_picking',
                                   picking_id=picking.id).get('success'))
        done_lines = picking.move_line_ids
        res = self._call('validate_picking', picking_id=picking.id)
        self.assertIn('déjà', res.get('error', ''))
        # Rien ne bouge sur un bon terminé : ni quantité, ni ligne.
        res = self._call('update_line_qty', picking_id=picking.id,
                         product_id=self.product.id, qty=1)
        self.assertIn('déjà', res.get('error', ''))
        picking.invalidate_recordset()
        self.assertEqual(picking.move_line_ids, done_lines)
        self.assertEqual(sum(done_lines.mapped('quantity')), 4)
        self.assertEqual(self.env['oski.barcode.scan.log'].search_count([
            ('picking_id', '=', picking.id), ('action', '=', 'validate')]), 1)

    def test_partial_scan_ships_only_scanned_quantity(self):
        """1 scanné sur 4 réservés : seule l'unité scannée part, reliquat de 3."""
        picking = self._delivery(4)
        self.authenticate('oski_bc_op', 'oski_bc_op')
        self._call('update_line_qty', picking_id=picking.id,
                   product_id=self.product.id, qty=1)
        res = self._call('validate_picking', picking_id=picking.id)
        self.assertTrue(res.get('success') and res.get('is_partial'), res)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.move_ids.quantity, 1)
        backorder = self.env['stock.picking'].search(
            [('backorder_id', '=', picking.id)])
        self.assertEqual(backorder.move_ids.product_uom_qty, 3)

    def test_negative_quantity_refused(self):
        picking = self._delivery(2)
        self.authenticate('oski_bc_op', 'oski_bc_op')
        res = self._call('update_line_qty', picking_id=picking.id,
                         product_id=self.product.id, qty=-3)
        self.assertIn('négative', res.get('error', ''))
        self.assertGreaterEqual(min(picking.move_line_ids.mapped('quantity')), 0)

    def test_ambiguous_location_name(self):
        Location = self.env['stock.location']
        parent2 = Location.create({'name': 'Zone B', 'usage': 'internal',
                                   'location_id': self.stock.id})
        Location.create({'name': 'OSKI-DUP', 'usage': 'internal',
                         'location_id': self.stock.id})
        Location.create({'name': 'OSKI-DUP', 'usage': 'internal',
                         'location_id': parent2.id})
        self.authenticate('oski_bc_op', 'oski_bc_op')
        res = self._call('scan_location', barcode='OSKI-DUP')
        self.assertFalse(res['found'])
        self.assertTrue(res.get('ambiguous'))
        self.assertIn('plusieurs', res.get('message', ''))

    def test_transfer_rejects_bad_input(self):
        dest = self.env['stock.location'].create({
            'name': 'Dest garde', 'usage': 'internal',
            'location_id': self.stock.id})
        # Type « transfert interne » actif (désactivé sans multi-emplacements)
        self.env.ref('stock.picking_type_internal').active = True
        self.authenticate('oski_bc_op', 'oski_bc_op')
        Picking = self.env['stock.picking']
        before = Picking.search_count([])
        res = self._call('create_transfer', src_location_id=self.stock.id,
                         dest_location_id=dest.id,
                         items=[{'product_id': self.product.id, 'qty': 0}])
        self.assertIn('error', res)
        res = self._call('create_transfer', src_location_id=self.stock.id,
                         dest_location_id=self.stock.id,
                         items=[{'product_id': self.product.id, 'qty': 1}])
        self.assertIn('error', res)
        self.assertEqual(Picking.search_count([]), before)
        res = self._call('create_transfer', src_location_id=self.stock.id,
                         dest_location_id=dest.id,
                         items=[{'product_id': self.product.id, 'qty': 1}])
        self.assertTrue(res.get('success'), res)
        transfer = Picking.browse(res['picking_id'])
        lines = self._call('get_picking_lines', picking_id=transfer.id)['lines']
        self.assertEqual(lines[0]['done_qty'], 1)
        self.assertTrue(self._call('validate_picking',
                                   picking_id=transfer.id).get('success'))
        self.assertEqual(transfer.state, 'done')

    def test_inventory_negative_count_refused(self):
        self.authenticate('admin', 'admin')
        res = self._call('apply_inventory', location_id=self.stock.id,
                         items=[{'product_id': self.product.id,
                                 'counted_qty': -1}])
        self.assertIn('error', res)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.product, self.stock), 4)

    def test_other_company_picking_is_invisible(self):
        """Un opérateur de la société A ne lit ni ne modifie un bon de B :
        réponse « introuvable » propre, pas de trace d'accès, aucune écriture."""
        company_b = self.env['res.company'].create({'name': 'Société B garde'})
        wh_b = self.env['stock.warehouse'].search(
            [('company_id', '=', company_b.id)], limit=1)
        product_b = self.env['product.product'].create({
            'name': 'Article B', 'is_storable': True})
        picking_b = self.env['stock.picking'].create({
            'picking_type_id': wh_b.out_type_id.id,
            'location_id': wh_b.lot_stock_id.id,
            'location_dest_id': self.customers.id,
            'company_id': company_b.id,
            'move_ids': [(0, 0, {
                'name': 'oski barcode',
                'product_id': product_b.id, 'product_uom_qty': 1,
                'product_uom': product_b.uom_id.id,
                'location_id': wh_b.lot_stock_id.id,
                'location_dest_id': self.customers.id,
                'company_id': company_b.id})],
        })
        picking_b.action_confirm()
        self.authenticate('oski_bc_op', 'oski_bc_op')
        for route, params in (
                ('get_picking_lines', {}),
                ('update_line_qty', {'product_id': product_b.id, 'qty': 1}),
                ('validate_picking', {}),
                ('get_report_url', {})):
            res = self._call(route, picking_id=picking_b.id, **params)
            self.assertIn('introuvable', res.get('error', ''), route)
        self.assertFalse(picking_b.move_line_ids.filtered('quantity'))
        res = self._call('scan_product', barcode='OSKIGUARD01',
                         picking_id=picking_b.id)
        self.assertFalse(res.get('in_picking'))

    def test_menu_restricted_to_stock_users(self):
        menu = self.env.ref('oski_stock_barcode.menu_barcode_root')
        self.assertIn(self.env.ref('stock.group_stock_user'), menu.groups_id)
