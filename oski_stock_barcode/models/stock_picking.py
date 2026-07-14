from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    barcode = fields.Char(
        string='Code-barres', copy=False, index=True,
        compute='_compute_barcode', store=True,
    )

    @api.depends('name')
    def _compute_barcode(self):
        for picking in self:
            picking.barcode = picking.name or ''
