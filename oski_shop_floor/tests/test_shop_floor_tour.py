from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestShopFloorTour(HttpCase):

    def test_shop_floor_flow_tour(self):
        wc = self.env['mrp.workcenter'].create({'name': 'Poste Tour'})
        component = self.env['product.product'].create({
            'name': 'Composant Tour', 'type': 'consu', 'is_storable': True, 'barcode': 'TOURCOMP',
        })
        finished = self.env['product.product'].create({
            'name': 'Fini Tour', 'type': 'consu', 'is_storable': True,
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0, 'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})],
            'operation_ids': [(0, 0, {'name': 'Op', 'workcenter_id': wc.id})],
        })
        # Lie la ligne de composant à l'opération créée : sans ce lien,
        # stock.move.operation_id (donc workorder_id) reste vide et
        # move_raw_ids du poste de travail ne contient rien (cf.
        # test_shop_floor_server.py / mrp_production._update_moves).
        # Sans components, .o_sf_comp_add ne se rend jamais côté OWL.
        bom.bom_line_ids.operation_id = bom.operation_ids[0]
        mo = self.env['mrp.production'].create({
            'product_id': finished.id, 'product_qty': 1.0, 'bom_id': bom.id,
        })
        mo.action_confirm()

        self.env.ref('base.user_admin').group_ids |= self.env.ref('mrp.group_mrp_user')
        self.start_tour('/odoo/action-oski_shop_floor.action_shop_floor',
                        'oski_shop_floor_tour', login='admin')
