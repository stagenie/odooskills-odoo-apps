from odoo import fields, models


class BarcodeScanLog(models.Model):
    _name = 'oski.barcode.scan.log'
    _description = 'Journal des scans code-barres'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Opérateur', required=True, index=True,
        default=lambda self: self.env.user)
    action = fields.Selection([
        ('receipt', 'Réception'),
        ('delivery', 'Expédition'),
        ('inventory', 'Inventaire'),
        ('transfer', 'Transfert'),
        ('serial_gen', 'Génération série'),
        ('validate', 'Validation'),
    ], string='Action', required=True)
    picking_id = fields.Many2one('stock.picking', string='Transfert',
                                 ondelete='set null')
    product_id = fields.Many2one('product.product', string='Article',
                                 ondelete='set null')
    lot_id = fields.Many2one('stock.lot', string='Lot/N° série',
                             ondelete='set null')
    quantity = fields.Float(string='Quantité')
    note = fields.Char(string='Note')
