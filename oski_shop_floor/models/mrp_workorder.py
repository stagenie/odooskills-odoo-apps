from odoo import _, api, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # Champs recalculés sans @api.depends côté noyau mrp (is_user_working,
    # working_user_ids, last_working_user_id) : leur cache n'est jamais
    # invalidé automatiquement quand un mrp.workcenter.productivity est
    # créé/fermé par button_start()/button_pending(). Sans invalidation
    # manuelle après ces appels, sf_get_detail() renverrait une valeur
    # is_user_working périmée dans le même environnement (même transaction).
    _SF_STALE_COMPUTE_FIELDS = ('is_user_working', 'working_user_ids', 'last_working_user_id')

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

    def sf_start(self):
        self.ensure_one()
        self.button_start()
        self.invalidate_recordset(self._SF_STALE_COMPUTE_FIELDS)
        return self.sf_get_detail()

    def sf_pause(self):
        self.ensure_one()
        self.button_pending()
        self.invalidate_recordset(self._SF_STALE_COMPUTE_FIELDS)
        return self.sf_get_detail()

    def sf_finish(self):
        self.ensure_one()
        # button_finish() du noyau mrp ne fait rien lever : il ignore
        # silencieusement les OT déjà 'done'/'cancel' et termine sans erreur
        # un OT jamais démarré ('ready'/'waiting'). Le flux tactile Shop
        # Floor exige explicitement un démarrage préalable : on impose la
        # règle nous-mêmes plutôt que de compter sur le natif.
        if self.state != 'progress':
            raise UserError(_("Impossible de terminer un ordre de travail qui n'est pas en cours."))
        self.button_finish()
        next_order = self.search([
            ('workcenter_id', '=', self.workcenter_id.id),
            ('state', '=', 'ready'),
            ('id', '!=', self.id),
        ], limit=1)
        detail = self.sf_get_detail()
        detail['next_order_id'] = next_order.id or False
        return detail

    def sf_set_qty(self, qty):
        self.ensure_one()
        self.qty_producing = qty
        return self.sf_get_detail()
