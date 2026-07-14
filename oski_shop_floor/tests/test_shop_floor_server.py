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
