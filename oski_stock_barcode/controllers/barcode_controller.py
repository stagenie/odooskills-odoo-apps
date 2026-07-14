import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AdiStockBarcodeController(http.Controller):

    # ══════════════════════════════════════════════════════════════
    # JOURNALISATION DES SCANS (best-effort)
    # ══════════════════════════════════════════════════════════════
    def _log_scan(self, action, picking=False, product=False, lot=False,
                  quantity=0.0, note=''):
        """Journalise un scan. Best-effort : n'interrompt jamais l'opération
        (le savepoint isole toute erreur du log de la transaction métier)."""
        try:
            with request.env.cr.savepoint():
                request.env['oski.barcode.scan.log'].create({
                    'action': action,
                    'picking_id': picking.id if picking else False,
                    'product_id': product.id if product else False,
                    'lot_id': lot.id if lot else False,
                    'quantity': quantity,
                    'note': note or '',
                })
        except Exception:
            _logger.warning("scan log failed", exc_info=True)

    # ══════════════════════════════════════════════════════════════
    # COMPTEURS PAGE D'ACCUEIL
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/picking_counts', type='jsonrpc', auth='user')
    def get_picking_counts(self):
        Picking = request.env['stock.picking']
        waiting_states = ('draft', 'confirmed', 'assigned', 'waiting')
        counts = {}
        for code in ('incoming', 'outgoing', 'internal'):
            counts[code] = Picking.search_count([
                ('picking_type_id.code', '=', code),
                ('state', 'in', waiting_states),
            ])
        return counts

    # ══════════════════════════════════════════════════════════════
    # PICKINGS — LISTE ENRICHIE
    # ══════════════════════════════════════════════════════════════
    def _prepare_picking_data(self, picking):
        """Prepare les donnees d'un picking — overridable par modules heritants."""
        moves = picking.move_ids
        total_lines = len(moves)
        done_lines = 0
        total_qty_demand = 0
        total_qty_done = 0
        for move in moves:
            done_qty = sum(move.move_line_ids.mapped('quantity'))
            total_qty_demand += move.product_uom_qty
            total_qty_done += done_qty
            if done_qty >= move.product_uom_qty and move.product_uom_qty > 0:
                done_lines += 1
        return {
            'id': picking.id,
            'name': picking.name,
            'barcode': picking.barcode or picking.name or '',
            'partner_name': picking.partner_id.name if picking.partner_id else '',
            'origin': picking.origin or '',
            'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else '',
            'state': picking.state,
            'total_lines': total_lines,
            'done_lines': done_lines,
            'total_qty_demand': total_qty_demand,
            'total_qty_done': total_qty_done,
        }

    @http.route('/oski_stock_barcode/get_pickings', type='jsonrpc', auth='user')
    def get_pickings(self, picking_type_code):
        pickings = request.env['stock.picking'].search(
            domain=[
                ('picking_type_id.code', '=', picking_type_code),
                ('state', 'in', ('draft', 'confirmed', 'assigned', 'waiting')),
            ],
            order='scheduled_date asc, id asc',
            limit=50,
        )
        return [self._prepare_picking_data(p) for p in pickings]

    @http.route('/oski_stock_barcode/scan_picking', type='jsonrpc', auth='user')
    def scan_picking(self, barcode, picking_type_code=False):
        """Recherche un picking par barcode (= son name)."""
        domain = [
            ('barcode', '=', barcode),
            ('state', 'in', ('draft', 'confirmed', 'assigned', 'waiting')),
        ]
        if picking_type_code:
            domain.append(('picking_type_id.code', '=', picking_type_code))
        picking = request.env['stock.picking'].search(domain, limit=1)
        if not picking:
            # Fallback : chercher par name directement
            domain[0] = ('name', '=', barcode)
            picking = request.env['stock.picking'].search(domain, limit=1)
        if not picking:
            return {'found': False}
        return {'found': True, 'picking': self._prepare_picking_data(picking)}

    # ══════════════════════════════════════════════════════════════
    # PICKING LINES — ENRICHI AVEC DISPONIBILITE
    # ══════════════════════════════════════════════════════════════
    def _prepare_line_data(self, move):
        """Prepare les donnees d'une ligne — overridable par lot module."""
        move_lines = move.move_line_ids
        done_qty = sum(move_lines.mapped('quantity'))
        reserved_qty = sum(move_lines.mapped('quantity')) if move.state == 'assigned' else 0

        # Disponibilite depuis le quant source
        available_qty = 0
        if move.location_id:
            quant = request.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', move.location_id.id),
            ], limit=1)
            if quant:
                available_qty = quant.available_quantity

        return {
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_name': move.product_id.display_name,
            'product_barcode': move.product_id.barcode or '',
            'demand_qty': move.product_uom_qty,
            'done_qty': done_qty,
            'reserved_qty': move.product_uom_qty if move.state == 'assigned' else 0,
            'available_qty': available_qty,
            'uom_name': move.product_uom.name if move.product_uom else '',
        }

    @http.route('/oski_stock_barcode/get_picking_lines', type='jsonrpc', auth='user')
    def get_picking_lines(self, picking_id):
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking introuvable'}

        lines = [self._prepare_line_data(m) for m in picking.move_ids]
        return {
            'picking_id': picking.id,
            'picking_name': picking.name,
            'partner_name': picking.partner_id.name or '',
            'origin': picking.origin or '',
            'state': picking.state,
            'lines': lines,
        }

    @http.route('/oski_stock_barcode/update_line_qty', type='jsonrpc', auth='user')
    def update_line_qty(self, picking_id, product_id, qty):
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking introuvable'}

        move = picking.move_ids.filtered(
            lambda m: m.product_id.id == product_id
        )
        if not move:
            return {'error': 'Article non trouvé dans ce picking'}

        move = move[0]

        # Contrôle de disponibilité pour les sorties (outgoing/internal)
        if picking.picking_type_id.code in ('outgoing', 'internal'):
            quant = request.env['stock.quant'].search([
                ('product_id', '=', product_id),
                ('location_id', '=', move.location_id.id),
            ], limit=1)
            available = quant.available_quantity if quant else 0
            if qty > available:
                return {
                    'error': f'Stock insuffisant : {available} disponible(s) pour {move.product_id.display_name}',
                    'available_qty': available,
                }

        move_line = move.move_line_ids[:1]
        if move_line:
            move_line.quantity = qty
        else:
            request.env['stock.move.line'].create({
                'move_id': move.id,
                'picking_id': picking.id,
                'product_id': product_id,
                'quantity': qty,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
            })

        code = picking.picking_type_id.code
        action = 'delivery' if code == 'outgoing' else (
            'transfer' if code == 'internal' else 'receipt')
        self._log_scan(action, picking=picking, product=move.product_id,
                       quantity=qty)
        return {'success': True}

    @http.route('/oski_stock_barcode/validate_picking', type='jsonrpc', auth='user')
    def validate_picking(self, picking_id, create_backorder=True):
        """Valide un picking. Si partiel, crée un reliquat (backorder) automatiquement.

        :param create_backorder: True = créer reliquat, False = annuler le reste
        """
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking introuvable'}

        # Vérifier qu'il y a au moins une quantité saisie
        has_qty = any(
            sum(m.move_line_ids.mapped('quantity')) > 0
            for m in picking.move_ids
        )
        if not has_qty:
            return {'error': 'Aucune quantité saisie'}

        # Contrôle de disponibilité pour les sorties avant validation
        if picking.picking_type_id.code in ('outgoing', 'internal'):
            for move in picking.move_ids:
                done_qty = sum(move.move_line_ids.mapped('quantity'))
                if done_qty <= 0:
                    continue
                quant = request.env['stock.quant'].search([
                    ('product_id', '=', move.product_id.id),
                    ('location_id', '=', move.location_id.id),
                ], limit=1)
                available = quant.available_quantity if quant else 0
                if done_qty > available:
                    return {
                        'error': f'Stock insuffisant pour {move.product_id.display_name}: '
                                 f'{done_qty} demandé(s), {available} disponible(s)',
                    }

        # Détecter si la validation est partielle
        is_partial = any(
            sum(m.move_line_ids.mapped('quantity')) < m.product_uom_qty
            for m in picking.move_ids
            if m.product_uom_qty > 0
        )

        self._log_scan('validate', picking=picking)

        try:
            if is_partial:
                # Bypass le wizard backorder — on gère directement
                ctx = {
                    'skip_backorder': True,
                    'button_validate_picking_ids': picking.ids,
                }
                if not create_backorder:
                    ctx['picking_ids_not_to_backorder'] = picking.ids
                picking.with_context(**ctx).button_validate()

                backorder = request.env['stock.picking'].search([
                    ('backorder_id', '=', picking.id),
                    ('state', 'not in', ('done', 'cancel')),
                ], limit=1)

                return {
                    'success': True,
                    'state': picking.state,
                    'is_partial': True,
                    'backorder_created': bool(backorder),
                    'backorder_name': backorder.name if backorder else '',
                }
            else:
                picking.button_validate()
                return {'success': True, 'state': picking.state, 'is_partial': False}
        except Exception as e:
            _logger.warning("Validation picking %s failed: %s", picking.name, e)
            return {'error': str(e)}

    # ══════════════════════════════════════════════════════════════
    # RECHERCHE PRODUIT
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/scan_product', type='jsonrpc', auth='user')
    def scan_product(self, barcode, picking_id=False):
        Product = request.env['product.product']
        product = Product.search([('barcode', '=', barcode)], limit=1)
        if not product:
            return {'found': False}

        result = {
            'found': True,
            'id': product.id,
            'name': product.display_name,
            'barcode': product.barcode,
            'default_code': product.default_code or '',
            'uom_name': product.uom_id.name if product.uom_id else '',
            'is_storable': product.is_storable,
        }

        if picking_id:
            picking = request.env['stock.picking'].browse(picking_id)
            move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
            if move:
                move = move[0]
                done_qty = sum(move.move_line_ids.mapped('quantity'))
                result['in_picking'] = True
                result['move_id'] = move.id
                result['demand_qty'] = move.product_uom_qty
                result['done_qty'] = done_qty
            else:
                result['in_picking'] = False

        return result

    @http.route('/oski_stock_barcode/search_products', type='jsonrpc', auth='user')
    def search_products(self, query, picking_id=False, storable_only=False, limit=10):
        Product = request.env['product.product']
        domain = []
        if storable_only:
            domain = [('is_storable', '=', True)]
        results = Product.name_search(name=query, domain=domain, operator='ilike', limit=limit)
        products = []
        for pid, pname in results:
            prod = Product.browse(pid)
            products.append({
                'id': pid,
                'name': pname,
                'barcode': prod.barcode or '',
                'default_code': prod.default_code or '',
                'is_storable': prod.is_storable,
            })
        return products

    # ══════════════════════════════════════════════════════════════
    # CONSULTATION PRODUIT
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/get_product_info', type='jsonrpc', auth='user')
    def get_product_info(self, product_id):
        """Retourne les infos détaillées d'un produit avec stock par emplacement."""
        product = request.env['product.product'].browse(product_id)
        if not product.exists():
            return {'error': 'Article introuvable'}

        # Stock par emplacement interne
        quants = request.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id.usage', '=', 'internal'),
        ], order='location_id')
        locations = []
        for q in quants:
            if q.quantity == 0 and q.reserved_quantity == 0:
                continue
            locations.append({
                'location_id': q.location_id.id,
                'location_name': q.location_id.complete_name,
                'quantity': q.quantity,
                'reserved_quantity': q.reserved_quantity,
                'available_quantity': q.available_quantity,
            })

        # Stock total
        total_qty = sum(l['quantity'] for l in locations)
        total_reserved = sum(l['reserved_quantity'] for l in locations)
        total_available = sum(l['available_quantity'] for l in locations)

        return {
            'id': product.id,
            'name': product.display_name,
            'default_code': product.default_code or '',
            'barcode': product.barcode or '',
            'list_price': product.list_price,
            'standard_price': product.standard_price,
            'uom_name': product.uom_id.name if product.uom_id else '',
            'categ_name': product.categ_id.name if product.categ_id else '',
            'is_storable': product.is_storable,
            'has_image': bool(product.image_128),
            'image_url': f'/web/image/product.product/{product.id}/image_128',
            'total_qty': total_qty,
            'total_reserved': total_reserved,
            'total_available': total_available,
            'locations': locations,
        }

    @http.route('/oski_stock_barcode/get_product_moves', type='jsonrpc', auth='user')
    def get_product_moves(self, product_id, limit=10):
        """Derniers mouvements réalisés d'un produit."""
        limit = max(1, min(int(limit or 10), 50))
        lines = request.env['stock.move.line'].search([
            ('product_id', '=', product_id), ('state', '=', 'done')],
            order='date desc', limit=limit)
        moves = []
        for ml in lines:
            moves.append({
                'date': ml.date.strftime('%Y-%m-%d %H:%M') if ml.date else '',
                'quantity': ml.quantity,
                'location': ml.location_id.complete_name,
                'location_dest': ml.location_dest_id.complete_name,
                'picking_name': ml.picking_id.name if ml.picking_id else '',
                'lot_name': ml.lot_id.name if ml.lot_id else '',
            })
        return {'moves': moves}

    # ══════════════════════════════════════════════════════════════
    # CONSULTATION EMPLACEMENT
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/scan_location', type='jsonrpc', auth='user')
    def scan_location(self, barcode):
        """Cherche un emplacement par barcode ou nom."""
        Location = request.env['stock.location']
        loc = Location.search([
            ('barcode', '=', barcode),
            ('usage', '=', 'internal'),
        ], limit=1)
        if not loc:
            loc = Location.search([
                ('name', '=', barcode),
                ('usage', '=', 'internal'),
            ], limit=1)
        if not loc:
            return {'found': False}
        return {'found': True, 'id': loc.id, 'name': loc.complete_name}

    @http.route('/oski_stock_barcode/get_location_info', type='jsonrpc', auth='user')
    def get_location_info(self, location_id):
        """Retourne les infos d'un emplacement avec son contenu stock."""
        location = request.env['stock.location'].browse(location_id)
        if not location.exists():
            return {'error': 'Emplacement introuvable'}

        quants = request.env['stock.quant'].search([
            ('location_id', '=', location_id),
            ('product_id.is_storable', '=', True),
        ], order='product_id')

        # Grouper par produit
        grouped = {}
        for q in quants:
            if q.quantity == 0 and q.reserved_quantity == 0:
                continue
            pid = q.product_id.id
            if pid in grouped:
                grouped[pid]['quantity'] += q.quantity
                grouped[pid]['reserved_quantity'] += q.reserved_quantity
                grouped[pid]['available_quantity'] += q.available_quantity
            else:
                grouped[pid] = {
                    'product_id': pid,
                    'product_name': q.product_id.display_name,
                    'default_code': q.product_id.default_code or '',
                    'barcode': q.product_id.barcode or '',
                    'quantity': q.quantity,
                    'reserved_quantity': q.reserved_quantity,
                    'available_quantity': q.available_quantity,
                }

        products = list(grouped.values())
        total_qty = sum(p['quantity'] for p in products)
        total_available = sum(p['available_quantity'] for p in products)

        return {
            'id': location.id,
            'name': location.complete_name,
            'barcode': location.barcode or '',
            'total_products': len(products),
            'total_qty': total_qty,
            'total_available': total_available,
            'products': products,
        }

    # ══════════════════════════════════════════════════════════════
    # INVENTAIRE
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/get_locations', type='jsonrpc', auth='user')
    def get_locations(self):
        locations = request.env['stock.location'].search_read(
            domain=[('usage', '=', 'internal')],
            fields=['name', 'complete_name', 'barcode'],
            order='complete_name',
        )
        return locations

    @http.route('/oski_stock_barcode/get_location_quants', type='jsonrpc', auth='user')
    def get_location_quants(self, location_id):
        """Retourne les articles stockables d'un emplacement, groupés par produit."""
        quants = request.env['stock.quant'].search([
            ('location_id', '=', location_id),
            ('product_id.is_storable', '=', True),
            ('quantity', '!=', 0),
        ], order='product_id')
        # Grouper par produit pour éviter les doublons (lots, paquets...)
        grouped = {}
        for q in quants:
            pid = q.product_id.id
            if pid in grouped:
                grouped[pid]['quantity'] += q.quantity
                grouped[pid]['reserved_quantity'] += q.reserved_quantity
                grouped[pid]['available_quantity'] += q.available_quantity
            else:
                grouped[pid] = {
                    'product_id': pid,
                    'product_name': q.product_id.display_name,
                    'product_barcode': q.product_id.barcode or '',
                    'default_code': q.product_id.default_code or '',
                    'quantity': q.quantity,
                    'reserved_quantity': q.reserved_quantity,
                    'available_quantity': q.available_quantity,
                    'counted_qty': False,
                }
        return list(grouped.values())

    @http.route('/oski_stock_barcode/get_quant_info', type='jsonrpc', auth='user')
    def get_quant_info(self, product_id, location_id):
        quant = request.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
        ], limit=1)
        return {
            'quantity': quant.quantity if quant else 0,
            'reserved_quantity': quant.reserved_quantity if quant else 0,
            'available_quantity': quant.available_quantity if quant else 0,
        }

    @http.route('/oski_stock_barcode/apply_inventory', type='jsonrpc', auth='user')
    def apply_inventory(self, location_id, items):
        """Applique l'inventaire et crée les mouvements de stock (traçabilité).

        Utilise _apply_inventory() directement pour éviter le wizard
        de conflit qui ne fonctionne pas en RPC.
        Chaque ajustement génère un stock.move validé dans le journal.
        """
        Quant = request.env['stock.quant']
        quants_to_apply = Quant
        applied_count = 0

        for item in items:
            quant = Quant.search([
                ('product_id', '=', item['product_id']),
                ('location_id', '=', location_id),
            ], limit=1)
            if not quant:
                quant = Quant.create({
                    'product_id': item['product_id'],
                    'location_id': location_id,
                    'inventory_quantity': item['counted_qty'],
                })
            else:
                quant.inventory_quantity = item['counted_qty']
            quant.inventory_quantity_set = True
            quants_to_apply |= quant

        if quants_to_apply:
            try:
                # Appel direct — crée des stock.move validés (traçabilité complète)
                quants_to_apply._apply_inventory()
                applied_count = len(quants_to_apply)
            except Exception as e:
                _logger.warning("Inventaire barcode failed: %s", e)
                return {'error': str(e)}

        self._log_scan('inventory', note=f'{applied_count} ligne(s)')
        return {'success': True, 'applied_count': applied_count}

    # ══════════════════════════════════════════════════════════════
    # TRANSFERT INTERNE
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/create_transfer', type='jsonrpc', auth='user')
    def create_transfer(self, src_location_id, dest_location_id, items):
        """Crée un picking de transfert interne, confirme et assigne.

        Ne valide PAS — l'opérateur peut ajuster les quantités puis
        appeler validate_picking pour valider (avec backorder si partiel).
        """
        PickingType = request.env['stock.picking.type']
        picking_type = PickingType.search([
            ('code', '=', 'internal'),
            ('company_id', '=', request.env.company.id),
        ], limit=1)
        if not picking_type:
            return {'error': 'Aucun type de transfert interne trouvé'}

        # Contrôle de disponibilité avant création
        Quant = request.env['stock.quant']
        Product = request.env['product.product']
        errors = []
        for item in items:
            product = Product.browse(item['product_id'])
            quant = Quant.search([
                ('product_id', '=', item['product_id']),
                ('location_id', '=', src_location_id),
            ], limit=1)
            available = quant.available_quantity if quant else 0
            if item['qty'] > available:
                errors.append(
                    f'{product.display_name}: {item["qty"]} demandé(s), {available} disponible(s)'
                )
        if errors:
            return {'error': 'Stock insuffisant:\n' + '\n'.join(errors)}

        picking = request.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': src_location_id,
            'location_dest_id': dest_location_id,
        })

        for item in items:
            product = Product.browse(item['product_id'])
            request.env['stock.move'].create({
                'product_id': product.id,
                'product_uom_qty': item['qty'],
                'product_uom': product.uom_id.id,
                'location_id': src_location_id,
                'location_dest_id': dest_location_id,
                'picking_id': picking.id,
            })

        picking.action_confirm()
        picking.action_assign()

        # Pré-remplir les quantités sur les move_lines
        for move in picking.move_ids:
            move_line = move.move_line_ids[:1]
            if move_line:
                move_line.quantity = move.product_uom_qty

        self._log_scan('transfer', picking=picking)
        return {
            'success': True,
            'picking_id': picking.id,
            'picking_name': picking.name,
        }

    @http.route('/oski_stock_barcode/get_report_url', type='jsonrpc', auth='user')
    def get_report_url(self, picking_id):
        """Retourne l'URL du rapport PDF pour un picking."""
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking introuvable'}

        # Utiliser le delivery slip pour les BL, le picking report pour le reste
        if picking.picking_type_id.code == 'outgoing':
            report_name = 'stock.report_deliveryslip'
        else:
            report_name = 'stock.action_report_picking'

        return {
            'url': f'/report/pdf/{report_name}/{picking.id}',
            'picking_name': picking.name,
        }

    # ══════════════════════════════════════════════════════════════
    # SESSION — JOURNAL DES SCANS DU JOUR (F7)
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/get_session_log', type='jsonrpc', auth='user')
    def get_session_log(self, day=False):
        """Journal des scans de l'utilisateur courant pour un jour donné."""
        import pytz
        from datetime import datetime, time

        Log = request.env['oski.barcode.scan.log']
        user = request.env.user
        today = fields.Date.context_today(Log)
        target = fields.Date.to_date(day) if day else today
        # create_date is stored UTC; convert the user's LOCAL day bounds to UTC
        # before comparing, otherwise the window is shifted by the tz offset.
        tz = pytz.timezone(request.env.user.tz or 'UTC')
        local_start = tz.localize(datetime.combine(target, time.min))
        local_end = tz.localize(datetime.combine(target, time.max))
        start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        end = local_end.astimezone(pytz.utc).replace(tzinfo=None)
        records = Log.search([
            ('user_id', '=', user.id),
            ('create_date', '>=', start), ('create_date', '<=', end)])
        labels = dict(Log._fields['action'].selection)
        lines, summary = [], {}
        for r in records:
            lines.append({
                'action': r.action,
                'action_label': labels.get(r.action, r.action),
                'product_name': r.product_id.display_name if r.product_id else '',
                'lot_name': r.lot_id.name if r.lot_id else '',
                'quantity': r.quantity,
                'picking_name': r.picking_id.name if r.picking_id else '',
                'time': r.create_date.strftime('%H:%M') if r.create_date else '',
            })
            s = summary.setdefault(r.action, {'count': 0, 'total_qty': 0.0,
                                              'label': labels.get(r.action, r.action)})
            s['count'] += 1
            s['total_qty'] += r.quantity or 0.0
        return {'lines': lines, 'summary': summary}
