import logging

from odoo import fields, http
from odoo.tools import float_compare
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
    # GARDE-FOUS (droits, société, état, disponibilité)
    # ══════════════════════════════════════════════════════════════
    def _get_record(self, model, record_id):
        """Enregistrement lisible par l'utilisateur, sinon recordset vide.

        ``search`` applique droits et règles multi-société : un id d'une autre
        société (ou forgé côté client) rend « introuvable » au lieu d'une
        AccessError, et ne permet ni lecture ni écriture."""
        Model = request.env[model]
        try:
            record_id = int(record_id)
        except (TypeError, ValueError):
            return Model
        return Model.search([('id', '=', record_id)], limit=1)

    def _get_picking(self, picking_id):
        return self._get_record('stock.picking', picking_id)

    def _closed_picking_error(self, picking):
        """Message si le bon n'est plus modifiable (double clic, rejeu réseau)."""
        if picking.state == 'done':
            return f'{picking.name} est déjà validé : aucune modification possible.'
        if picking.state == 'cancel':
            return f'{picking.name} est annulé : aucune modification possible.'
        return False

    def _move_done_qty(self, move):
        """Quantité scannée d'un mouvement (unité du mouvement).

        Depuis Odoo 17, ``stock.move.line.quantity`` porte aussi la RÉSERVATION :
        seul le drapeau ``picked`` distingue ce qui a été scanné. Les articles
        suivis (lot / n° de série) gardent la somme des lignes, gérée par
        oski_stock_barcode_lot."""
        if move.product_id.tracking != 'none':
            return sum(move.move_line_ids.mapped('quantity'))
        return move.quantity if move.picked else 0.0

    def _available_for_move(self, move):
        """Stock utilisable par ce mouvement (unité du mouvement) : le libre de
        l'emplacement source (sous-emplacements et lots compris) + ce que le
        mouvement a déjà réservé pour lui-même."""
        free = request.env['stock.quant']._get_available_quantity(
            move.product_id, move.location_id)
        free = move.product_id.uom_id._compute_quantity(
            free, move.product_uom, round=False)
        return free + move.quantity

    # ══════════════════════════════════════════════════════════════
    # COMPTEURS PAGE D'ACCUEIL
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/picking_counts', type='json', auth='user')
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
            done_qty = self._move_done_qty(move)
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

    @http.route('/oski_stock_barcode/get_pickings', type='json', auth='user')
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

    @http.route('/oski_stock_barcode/scan_picking', type='json', auth='user')
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
        done_qty = self._move_done_qty(move)
        # Disponible pour CE mouvement (sa propre réservation comprise)
        available_qty = self._available_for_move(move) if move.location_id else 0

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

    @http.route('/oski_stock_barcode/get_picking_lines', type='json', auth='user')
    def get_picking_lines(self, picking_id):
        picking = self._get_picking(picking_id)
        if not picking:
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

    @http.route('/oski_stock_barcode/update_line_qty', type='json', auth='user')
    def update_line_qty(self, picking_id, product_id, qty):
        picking = self._get_picking(picking_id)
        if not picking:
            return {'error': 'Picking introuvable'}
        closed = self._closed_picking_error(picking)
        if closed:
            return {'error': closed}
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            return {'error': 'Quantité invalide'}
        if qty < 0:
            return {'error': 'Quantité négative refusée'}

        move = picking.move_ids.filtered(
            lambda m: m.product_id.id == product_id
        )
        if not move:
            return {'error': 'Article non trouvé dans ce picking'}

        move = move[0]

        # Contrôle de disponibilité pour les sorties (outgoing/internal)
        if picking.picking_type_id.code in ('outgoing', 'internal'):
            available = self._available_for_move(move)
            if float_compare(qty, available, precision_rounding=move.product_uom.rounding) > 0:
                return {
                    'error': f'Stock insuffisant : {available} disponible(s) pour {move.product_id.display_name}',
                    'available_qty': available,
                }

        if float_compare(qty, 0, precision_rounding=move.product_uom.rounding) > 0:
            # quantity (inverse) ajuste réservation et lignes ; picked = « scanné ».
            move.quantity = qty
            move.picked = True
        else:
            move.picked = False
            if float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding) > 0:
                move.quantity = move.product_uom_qty

        code = picking.picking_type_id.code
        action = 'delivery' if code == 'outgoing' else (
            'transfer' if code == 'internal' else 'receipt')
        self._log_scan(action, picking=picking, product=move.product_id,
                       quantity=qty)
        return {'success': True}

    @http.route('/oski_stock_barcode/validate_picking', type='json', auth='user')
    def validate_picking(self, picking_id, create_backorder=True):
        """Valide un picking. Si partiel, crée un reliquat (backorder) automatiquement.

        :param create_backorder: True = créer reliquat, False = annuler le reste
        """
        picking = self._get_picking(picking_id)
        if not picking:
            return {'error': 'Picking introuvable'}
        closed = self._closed_picking_error(picking)
        if closed:
            return {'error': closed}

        # Vérifier qu'il y a au moins une quantité saisie
        done = {m.id: self._move_done_qty(m) for m in picking.move_ids}
        if not any(q > 0 for q in done.values()):
            return {'error': 'Aucune quantité saisie'}

        # Contrôle de disponibilité pour les sorties avant validation
        if picking.picking_type_id.code in ('outgoing', 'internal'):
            for move in picking.move_ids:
                done_qty = done[move.id]
                if done_qty <= 0:
                    continue
                available = self._available_for_move(move)
                if float_compare(done_qty, available, precision_rounding=move.product_uom.rounding) > 0:
                    return {
                        'error': f'Stock insuffisant pour {move.product_id.display_name}: '
                                 f'{done_qty} demandé(s), {available} disponible(s)',
                    }

        # Détecter si la validation est partielle
        is_partial = any(
            done[m.id] < m.product_uom_qty
            for m in picking.move_ids
            if m.product_uom_qty > 0
        )

        # Articles suivis (lots) : ce qui est saisi est pris. Les autres ne sont
        # « pris » que s'ils ont été scannés : la réservation seule ne part pas.
        to_pick = picking.move_ids.filtered(
            lambda m: done[m.id] > 0 and not m.picked)
        if to_pick:
            to_pick.picked = True

        ctx = {}
        if is_partial:
            # Bypass le wizard backorder — on gère directement
            ctx = {
                'skip_backorder': True,
                'button_validate_picking_ids': picking.ids,
            }
            if not create_backorder:
                ctx['picking_ids_not_to_backorder'] = picking.ids
        try:
            # Savepoint : un échec en cours de validation n'en laisse rien.
            with request.env.cr.savepoint():
                picking.with_context(**ctx).button_validate()
        except Exception as e:
            _logger.warning("Validation picking %s failed: %s", picking.name, e)
            return {'error': str(e)}
        if picking.state != 'done':
            # Un assistant (confirmation, SMS…) attend une réponse : rien n'est fait.
            return {'error': f'{picking.name} demande une confirmation : '
                             'terminez la validation depuis le bon dans Inventaire.'}

        self._log_scan('validate', picking=picking)
        if not is_partial:
            return {'success': True, 'state': picking.state, 'is_partial': False}
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

    # ══════════════════════════════════════════════════════════════
    # RECHERCHE PRODUIT
    # ══════════════════════════════════════════════════════════════
    @http.route('/oski_stock_barcode/scan_product', type='json', auth='user')
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
            picking = self._get_picking(picking_id)
            move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
            if move:
                move = move[0]
                done_qty = self._move_done_qty(move)
                result['in_picking'] = True
                result['move_id'] = move.id
                result['demand_qty'] = move.product_uom_qty
                result['done_qty'] = done_qty
            else:
                result['in_picking'] = False

        return result

    @http.route('/oski_stock_barcode/search_products', type='json', auth='user')
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
    @http.route('/oski_stock_barcode/get_product_info', type='json', auth='user')
    def get_product_info(self, product_id):
        """Retourne les infos détaillées d'un produit avec stock par emplacement."""
        product = self._get_record('product.product', product_id)
        if not product:
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

    @http.route('/oski_stock_barcode/get_product_moves', type='json', auth='user')
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
    @http.route('/oski_stock_barcode/scan_location', type='json', auth='user')
    def scan_location(self, barcode):
        """Cherche un emplacement par barcode ou nom."""
        Location = request.env['stock.location']
        loc = Location.search([
            ('barcode', '=', barcode),
            ('usage', '=', 'internal'),
        ], limit=2)
        if not loc:
            # Nom court : souvent répété (« Stock » de chaque entrepôt).
            loc = Location.search([
                ('name', '=', barcode),
                ('usage', '=', 'internal'),
            ], limit=2)
        if not loc:
            return {'found': False}
        if len(loc) > 1:
            return {
                'found': False, 'ambiguous': True,
                'message': f'« {barcode} » désigne plusieurs emplacements '
                           f'({", ".join(loc.mapped("complete_name"))}) : '
                           'scannez son code-barres ou choisissez-le dans la liste.',
            }
        return {'found': True, 'id': loc.id, 'name': loc.complete_name}

    @http.route('/oski_stock_barcode/get_location_info', type='json', auth='user')
    def get_location_info(self, location_id):
        """Retourne les infos d'un emplacement avec son contenu stock."""
        location = self._get_record('stock.location', location_id)
        if not location:
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
    @http.route('/oski_stock_barcode/get_locations', type='json', auth='user')
    def get_locations(self):
        locations = request.env['stock.location'].search_read(
            domain=[('usage', '=', 'internal')],
            fields=['name', 'complete_name', 'barcode'],
            order='complete_name',
        )
        return locations

    @http.route('/oski_stock_barcode/get_location_quants', type='json', auth='user')
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

    @http.route('/oski_stock_barcode/get_quant_info', type='json', auth='user')
    def get_quant_info(self, product_id, location_id):
        """Stock d'un article dans un emplacement (sous-emplacements et lots compris)."""
        product = self._get_record('product.product', product_id)
        location = self._get_record('stock.location', location_id)
        if not product or not location:
            return {'quantity': 0, 'reserved_quantity': 0, 'available_quantity': 0}
        Quant = request.env['stock.quant']
        quants = Quant._gather(product, location)
        return {
            'quantity': sum(quants.mapped('quantity')),
            'reserved_quantity': sum(quants.mapped('reserved_quantity')),
            'available_quantity': Quant._get_available_quantity(product, location),
        }

    @http.route('/oski_stock_barcode/apply_inventory', type='json', auth='user')
    def apply_inventory(self, location_id, items):
        """Applique l'inventaire et crée les mouvements de stock (traçabilité).

        Utilise _apply_inventory() directement pour éviter le wizard
        de conflit qui ne fonctionne pas en RPC.
        Chaque ajustement génère un stock.move validé dans le journal.
        """
        Quant = request.env['stock.quant']
        quants_to_apply = Quant
        applied_count = 0

        location = self._get_record('stock.location', location_id)
        if not location or location.usage != 'internal':
            return {'error': 'Emplacement introuvable'}
        for item in items:
            try:
                counted = float(item.get('counted_qty'))
            except (TypeError, ValueError):
                return {'error': 'Quantité comptée invalide'}
            if counted < 0:
                return {'error': 'Quantité comptée négative refusée'}

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
    @http.route('/oski_stock_barcode/create_transfer', type='json', auth='user')
    def create_transfer(self, src_location_id, dest_location_id, items):
        """Crée un picking de transfert interne, confirme et assigne.

        Ne valide PAS — l'opérateur peut ajuster les quantités puis
        appeler validate_picking pour valider (avec backorder si partiel).
        """
        src = self._get_record('stock.location', src_location_id)
        dest = self._get_record('stock.location', dest_location_id)
        if not src or not dest or src.usage != 'internal' or dest.usage != 'internal':
            return {'error': 'Emplacement introuvable'}
        if src == dest:
            return {'error': 'Emplacements source et destination identiques'}
        if not items:
            return {'error': 'Aucun article à transférer'}
        for item in items:
            try:
                qty = float(item.get('qty'))
            except (TypeError, ValueError):
                return {'error': 'Quantité invalide'}
            if qty <= 0:
                return {'error': 'Quantité nulle ou négative refusée'}
            if not self._get_record('product.product', item.get('product_id')):
                return {'error': 'Article introuvable'}

        # Type d'opération de l'entrepôt (donc de la société) de la source
        PickingType = request.env['stock.picking.type']
        picking_type = PickingType
        if src.warehouse_id:
            picking_type = PickingType.search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', src.warehouse_id.id),
            ], limit=1)
        if not picking_type:
            picking_type = PickingType.search([
                ('code', '=', 'internal'),
                ('company_id', '=', (src.company_id or request.env.company).id),
            ], limit=1)
        if not picking_type:
            return {'error': 'Aucun type de transfert interne trouvé'}

        # Contrôle de disponibilité avant création
        Quant = request.env['stock.quant']
        Product = request.env['product.product']
        errors = []
        for item in items:
            product = Product.browse(item['product_id'])
            available = Quant._get_available_quantity(product, src)
            if item['qty'] > available:
                errors.append(
                    f'{product.display_name}: {item["qty"]} demandé(s), {available} disponible(s)'
                )
        if errors:
            return {'error': 'Stock insuffisant:\n' + '\n'.join(errors)}

        picking = request.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
        })

        for item in items:
            product = Product.browse(item['product_id'])
            request.env['stock.move'].create({
                'name': product.display_name,
                'product_id': product.id,
                'product_uom_qty': item['qty'],
                'product_uom': product.uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'picking_id': picking.id,
            })

        picking.action_confirm()
        picking.action_assign()

        # Pré-remplir : les quantités demandées sont considérées comme prises
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True

        self._log_scan('transfer', picking=picking)
        return {
            'success': True,
            'picking_id': picking.id,
            'picking_name': picking.name,
        }

    @http.route('/oski_stock_barcode/get_report_url', type='json', auth='user')
    def get_report_url(self, picking_id):
        """Retourne l'URL du rapport PDF pour un picking."""
        picking = self._get_picking(picking_id)
        if not picking:
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
    @http.route('/oski_stock_barcode/get_session_log', type='json', auth='user')
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
