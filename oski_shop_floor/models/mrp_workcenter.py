from odoo import api, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    @api.model
    def sf_get_workcenters(self):
        """Postes visibles + compteurs d'OT à faire/en cours (JSON-safe)."""
        result = []
        for wc in self.search([]):
            orders = self.env['mrp.workorder'].search([
                ('workcenter_id', '=', wc.id),
                ('state', 'in', ('ready', 'progress')),
            ])
            result.append({
                'id': wc.id,
                'name': wc.name,
                'code': wc.code or '',
                'working_state': wc.working_state,
                'count_ready': len(orders.filtered(lambda o: o.state == 'ready')),
                'count_progress': len(orders.filtered(lambda o: o.state == 'progress')),
            })
        return result
