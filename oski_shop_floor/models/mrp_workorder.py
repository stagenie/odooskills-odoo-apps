from odoo import api, models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    @api.model
    def sf_get_orders(self, workcenter_id):
        """OT ready/progress d'un poste (progress d'abord), JSON-safe."""
        orders = self.search([
            ('workcenter_id', '=', workcenter_id),
            ('state', 'in', ('ready', 'progress')),
        ])
        orders = orders.sorted(key=lambda o: (0 if o.state == 'progress' else 1, o.id))
        return [o._sf_order_card() for o in orders]

    def _sf_order_card(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'product_name': self.product_id.display_name,
            'production_name': self.production_id.name,
            'qty_production': self.qty_production,
            'qty_producing': self.qty_producing,
            'qty_produced': self.qty_produced,
            'state': self.state,
            'is_user_working': self.is_user_working,
            'duration_expected': self.duration_expected,
            'duration': self.duration,
        }

    def sf_get_detail(self):
        """Carte OT + composants (move_raw_ids) avec quantité consommée."""
        self.ensure_one()
        card = self._sf_order_card()
        components = []
        for move in self.move_raw_ids:
            qty_done = sum(move.move_line_ids.mapped('quantity'))
            components.append({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'tracking': move.product_id.tracking,
                'qty_demand': move.product_uom_qty,
                'qty_done': qty_done,
            })
        card['components'] = components
        return card
