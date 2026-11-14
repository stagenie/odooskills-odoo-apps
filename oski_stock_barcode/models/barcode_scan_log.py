from odoo import fields, models


class BarcodeScanLog(models.Model):
    _name = 'oski.barcode.scan.log'
    _description = 'Barcode Scan Log'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Operator', required=True, index=True,
        default=lambda self: self.env.user)
    action = fields.Selection([
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery'),
        ('inventory', 'Inventory'),
        ('transfer', 'Transfer'),
        ('serial_gen', 'Serial Generation'),
        ('validate', 'Validation'),
    ], string='Action', required=True)
    picking_id = fields.Many2one('stock.picking', string='Transfer',
                                 ondelete='set null')
    product_id = fields.Many2one('product.product', string='Item',
                                 ondelete='set null')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial No.',
                             ondelete='set null')
    quantity = fields.Float(string='Quantity')
    note = fields.Char(string='Note')
