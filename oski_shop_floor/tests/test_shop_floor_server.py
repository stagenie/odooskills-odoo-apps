from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestShopFloorServer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wc = cls.env['mrp.workcenter'].create({'name': 'Poste Test SF'})
        cls.component = cls.env['product.product'].create({
            'name': 'Composant SF', 'type': 'consu', 'is_storable': True,
        })
        cls.finished = cls.env['product.product'].create({
            'name': 'Produit Fini SF', 'type': 'consu', 'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': cls.component.id, 'product_qty': 2.0})],
            'operation_ids': [(0, 0, {'name': 'Op 1', 'workcenter_id': cls.wc.id})],
        })
        # Lie la ligne de composant à l'opération créée : sans ce lien,
        # stock.move.operation_id (donc workorder_id) reste vide et
        # move_raw_ids du poste de travail ne contient rien (cf. mrp_production
        # _update_moves : move_raw.operation_id = bom_line.operation_id).
        cls.bom.bom_line_ids.operation_id = cls.bom.operation_ids[0]
        cls.mo = cls.env['mrp.production'].create({
            'product_id': cls.finished.id,
            'product_qty': 1.0,
            'bom_id': cls.bom.id,
        })
        cls.mo.action_confirm()
        cls.wo = cls.mo.workorder_ids[0]

    def test_get_workcenters(self):
        rows = self.env['mrp.workcenter'].sf_get_workcenters()
        row = next(r for r in rows if r['id'] == self.wc.id)
        self.assertEqual(row['name'], 'Poste Test SF')
        self.assertEqual(row['count_ready'], 1)
        self.assertEqual(row['count_progress'], 0)

    def test_get_orders(self):
        rows = self.env['mrp.workorder'].sf_get_orders(self.wc.id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], self.wo.id)
        self.assertEqual(rows[0]['state'], 'ready')

    def test_get_detail_components(self):
        detail = self.wo.sf_get_detail()
        self.assertEqual(detail['id'], self.wo.id)
        self.assertEqual(len(detail['components']), 1)
        comp = detail['components'][0]
        self.assertEqual(comp['product_id'], self.component.id)
        self.assertEqual(comp['qty_demand'], 2.0)
        self.assertEqual(comp['qty_done'], 0.0)

    def test_get_detail_qty_done_nonzero(self):
        # Sans stock.move.line, qty_done=0.0 est trivialement vrai (liste
        # vide) et n'exercise pas la sommation sur le champ v19 `quantity`.
        # On crée une move_line avec une quantité non nulle pour vérifier
        # que sf_get_detail() lit bien `quantity` (et pas `qty_done`, champ
        # supprimé en v19) et ne double-compte pas.
        move = self.wo.move_raw_ids[0]
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'quantity': 1.5,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        })
        detail = self.wo.sf_get_detail()
        comp = next(c for c in detail['components'] if c['product_id'] == self.component.id)
        self.assertEqual(comp['qty_done'], 1.5)

    def test_start_sets_progress(self):
        detail = self.wo.sf_start()
        self.assertEqual(detail['state'], 'progress')
        self.assertTrue(detail['is_user_working'])

    def test_set_qty(self):
        self.wo.sf_start()
        detail = self.wo.sf_set_qty(1.0)
        self.assertEqual(detail['qty_producing'], 1.0)

    def test_pause_then_finish(self):
        self.wo.sf_start()
        paused = self.wo.sf_pause()
        self.assertFalse(paused['is_user_working'])
        self.wo.sf_start()
        self.wo.sf_set_qty(1.0)
        finished = self.wo.sf_finish()
        self.assertEqual(finished['state'], 'done')
        self.assertIn('next_order_id', finished)

    def test_finish_before_start_raises(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self.wo.sf_finish()

    def test_consume_sets_quantity(self):
        self.wo.sf_start()
        move = self.wo.move_raw_ids[0]
        detail = self.wo.sf_consume(move.id, 2.0)
        comp = next(c for c in detail['components'] if c['move_id'] == move.id)
        self.assertEqual(comp['qty_done'], 2.0)
        self.assertFalse(detail['needs_lot'])

    def test_consume_foreign_move_rejected(self):
        from odoo.exceptions import UserError
        other = self.env['stock.move'].create({
            'product_id': self.component.id,
            'product_uom_qty': 1.0, 'product_uom': self.component.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        with self.assertRaises(UserError):
            self.wo.sf_consume(other.id, 1.0)

    def test_scan_component_increments(self):
        self.component.barcode = 'SFCOMP01'
        self.wo.sf_start()
        # sf_start() -> button_start() fait passer qty_producing à une valeur
        # non nulle, ce qui déclenche _set_qty_producing() côté noyau mrp :
        # celui-ci PRÉ-REMPLIT automatiquement la quantité consommée du
        # composant (proposition de consommation attendue), même sans aucun
        # scan. On neutralise cette proposition pour tester le scan sur une
        # base à zéro (le pont barcode réel devra faire de même en amont).
        move = self.wo.move_raw_ids[0]
        move.move_line_ids.quantity = 0.0
        res = self.wo.sf_scan('SFCOMP01')
        self.assertTrue(res['found'])
        move = self.wo.move_raw_ids[0]
        comp = next(c for c in res['detail']['components'] if c['move_id'] == move.id)
        self.assertEqual(comp['qty_done'], 1.0)

    def test_scan_unknown_not_found(self):
        self.wo.sf_start()
        res = self.wo.sf_scan('NOPE')
        self.assertFalse(res['found'])
