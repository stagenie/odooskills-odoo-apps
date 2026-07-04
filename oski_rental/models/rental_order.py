from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class RentalOrder(models.Model):
    _name = 'oski.rental.order'
    _description = 'Location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(string='Référence', default='Nouveau', readonly=True, copy=False)
    partner_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Responsable', tracking=True,
        default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', string='Société', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_start = fields.Datetime(string='Début', required=True, tracking=True)
    date_end = fields.Datetime(string='Fin prévue', required=True, tracking=True)
    origin = fields.Selection([
        ('manual', 'Manuel'),
        ('website', 'Site web'),
    ], string='Origine', default='manual', readonly=True)
    state = fields.Selection([
        ('draft', 'Devis'),
        ('reserved', 'Réservée'),
        ('ongoing', 'En cours'),
        ('returned', 'Retournée'),
        ('done', 'Facturée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='draft', tracking=True, copy=False)
    line_ids = fields.One2many(
        'oski.rental.order.line', 'order_id', string='Lignes', copy=True)
    actual_return_date = fields.Datetime(string='Retour effectif', readonly=True, copy=False)
    is_late = fields.Boolean(string='En retard', compute='_compute_is_late')
    late_notified = fields.Boolean(copy=False)
    checkout_note = fields.Text(string='État des lieux — départ', copy=False)
    checkin_note = fields.Text(string='État des lieux — retour', copy=False)
    deposit_state = fields.Selection([
        ('none', 'Sans caution'),
        ('to_collect', 'À percevoir'),
        ('collected', 'Perçue'),
        ('refunded', 'Remboursée'),
    ], string='Caution', default='none', tracking=True, copy=False)
    amount_subtotal = fields.Monetary(
        string='Sous-total', compute='_compute_amounts', store=True)
    deposit_total = fields.Monetary(
        string='Total caution', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(
        string='Total', compute='_compute_amounts', store=True)
    invoice_ids = fields.Many2many(
        'account.move', string='Factures', copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.rental.order') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('line_ids.price_subtotal', 'line_ids.deposit', 'line_ids.late_amount')
    def _compute_amounts(self):
        for order in self:
            order.amount_subtotal = sum(order.line_ids.mapped('price_subtotal'))
            order.deposit_total = sum(order.line_ids.mapped('deposit'))
            order.amount_total = order.amount_subtotal + sum(
                order.line_ids.mapped('late_amount'))

    @api.depends('state', 'date_end', 'actual_return_date')
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for order in self:
            if order.state == 'ongoing':
                order.is_late = bool(order.date_end and order.date_end < now)
            elif order.state in ('returned', 'done'):
                order.is_late = bool(
                    order.actual_return_date and order.date_end
                    and order.actual_return_date > order.date_end)
            else:
                order.is_late = False

    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    def unlink(self):
        if any(order.state not in ('draft', 'cancelled') for order in self):
            raise UserError(
                "Seule une location en devis ou annulée peut être supprimée.")
        return super().unlink()

    def action_reserve(self):
        for order in self:
            if order.state != 'draft':
                raise UserError("Seul un devis peut être réservé.")
            if not order.line_ids:
                raise UserError("Ajoutez au moins une ligne de location.")
            order._check_conflicts()
            order.write({
                'state': 'reserved',
                'deposit_state': 'to_collect' if order.deposit_total else 'none',
            })

    def action_cancel(self):
        for order in self:
            if order.state not in ('draft', 'reserved'):
                raise UserError(
                    "Seule une location en devis ou réservée peut être annulée.")
            order.write({'state': 'cancelled'})

    def _check_conflicts(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.asset_id.check_availability(
                    line.date_start, line.date_end,
                    exclude_line_ids=self.line_ids.ids):
                raise UserError(
                    "Conflit : « %s » est indisponible du %s au %s "
                    "(réservation ou indisponibilité existante)." % (
                        line.asset_id.name, line.date_start, line.date_end))
            siblings = self.line_ids.filtered(
                lambda l: l.id != line.id and l.asset_id == line.asset_id)
            for other in siblings:
                if line.date_start < other.date_end \
                        and line.date_end > other.date_start:
                    raise UserError(
                        "Conflit interne : « %s » figure deux fois sur des "
                        "périodes qui se chevauchent." % line.asset_id.name)

    def action_open_checkout(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Départ — état des lieux',
            'res_model': 'oski.rental.checkout.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_open_checkin(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Retour — état des lieux',
            'res_model': 'oski.rental.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def _get_default_rental_product(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'oski_rental.default_product_id')
        product = self.env['product.product']
        if param and param.isdigit():
            product = product.browse(int(param)).exists()
        if not product:
            product = self.env.ref(
                'oski_rental.product_rental_default', raise_if_not_found=False)
        if not product:
            raise UserError(
                "Aucun article de facturation configuré "
                "(Paramètres > Location).")
        return product

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != 'returned':
            raise UserError("Seule une location retournée peut être facturée.")
        default_product = self._get_default_rental_product()
        invoice_lines = []
        for line in self.line_ids:
            product = line.asset_id.product_id or default_product
            label = "%s — du %s au %s" % (
                line.asset_id.name,
                line.date_start.strftime('%d/%m/%Y %H:%M'),
                line.date_end.strftime('%d/%m/%Y %H:%M'))
            invoice_lines.append(Command.create({
                'product_id': product.id,
                'name': label,
                'quantity': 1.0,
                'price_unit': line.price_subtotal,
            }))
            if line.late_amount:
                invoice_lines.append(Command.create({
                    'product_id': product.id,
                    'name': "Retard — %s" % line.asset_id.name,
                    'quantity': 1.0,
                    'price_unit': line.late_amount,
                }))
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'company_id': self.company_id.id,
            'invoice_line_ids': invoice_lines,
        })
        self.write({
            'state': 'done',
            'invoice_ids': [Command.link(move.id)],
        })
        return self.action_view_invoices()

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'create': False},
        }

    def action_refund_deposit(self):
        for order in self:
            if order.state not in ('returned', 'done') \
                    or order.deposit_state != 'collected':
                raise UserError(
                    "La caution ne peut être remboursée qu'après retour, "
                    "si elle a été perçue.")
            order.write({'deposit_state': 'refunded'})
