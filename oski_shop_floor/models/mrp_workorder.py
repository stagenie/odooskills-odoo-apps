from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # Champs recalculés sans @api.depends côté noyau mrp (is_user_working,
    # working_user_ids, last_working_user_id) : leur cache n'est jamais
    # invalidé automatiquement quand un mrp.workcenter.productivity est
    # créé/fermé par button_start()/button_pending(). Sans invalidation
    # manuelle après ces appels, sf_get_detail() renverrait une valeur
    # is_user_working périmée dans le même environnement (même transaction).
    _SF_STALE_COMPUTE_FIELDS = ('is_user_working', 'working_user_ids', 'last_working_user_id')

    # Odoo 18 : un OT non bloqué par une opération précédente est 'ready'
    # (composants réservés) ou 'waiting' (composants pas encore disponibles) ;
    # Odoo 19 ne garde que 'ready'. Les deux sont « à faire » à l'atelier.
    _SF_TODO_STATES = ('waiting', 'ready')

    @api.model
    def sf_get_orders(self, workcenter_id):
        """OT ready/progress d'un poste (progress d'abord), JSON-safe."""
        orders = self.search([
            ('workcenter_id', '=', workcenter_id),
            ('state', 'in', self._SF_TODO_STATES + ('progress',)),
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

    def _sf_check_input(self, qty):
        """Saisie de quantité : OT en cours et quantité positive ou nulle."""
        self.ensure_one()
        if self.state != 'progress':
            raise UserError(_("Démarrez l'ordre de travail avant de saisir des quantités."))
        if qty is None or qty < 0:
            raise UserError(_("La quantité ne peut pas être négative."))

    def sf_start(self):
        self.ensure_one()
        # Seul le PREMIER démarrage neutralise la proposition de consommation :
        # une reprise après pause, un double clic ou une requête rejouée ne
        # doivent pas effacer les composants déjà scannés.
        first_start = self.state != 'progress'
        self.button_start()
        # button_start() fixe qty_producing = qty_remaining, dont l'inverse
        # _set_qty_producing() (noyau mrp) pré-remplit automatiquement la
        # quantité consommée de chaque move non pické (proposition de
        # consommation attendue). Le flux Shop Floor est piloté par le scan
        # (comptage manuel composant par composant) : on neutralise cette
        # proposition pour que l'opérateur reparte de 0, sans droits élargis.
        # Les moves « picked » portent un comptage confirmé par l'opérateur
        # (lots posés avant le démarrage, cf. oski_shop_floor_barcode) : on ne
        # les efface pas.
        move_lines = self.move_raw_ids.filtered(lambda m: not m.picked).move_line_ids
        if first_start and move_lines:
            move_lines.quantity = 0
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
        self.invalidate_recordset(self._SF_STALE_COMPUTE_FIELDS)
        next_order = self.search([
            ('workcenter_id', '=', self.workcenter_id.id),
            ('state', 'in', self._SF_TODO_STATES),
            ('id', '!=', self.id),
        ], limit=1)
        detail = self.sf_get_detail()
        detail['next_order_id'] = next_order.id or False
        return detail

    def sf_set_qty(self, qty):
        self._sf_check_input(qty)
        self.qty_producing = qty
        return self.sf_get_detail()

    def sf_consume(self, move_id, qty):
        """Pose la quantité consommée sur un composant (move_raw_ids) de l'OT.

        Sécurité : le move DOIT appartenir aux composants de cet OT, sinon rejet.
        V1 : par produit uniquement ; si tracké lot/série, renvoie needs_lot=True
        (le pont barcode gèrera le lot) sans bloquer.
        """
        self._sf_check_input(qty)
        move = self.move_raw_ids.filtered(lambda m: m.id == move_id)
        if not move:
            raise UserError(_("Composant introuvable pour cet ordre de travail."))
        # La quantité affichée est la SOMME des lignes : la quantité saisie
        # devient ce total (première ligne = qty, les autres à 0), sinon
        # « +1 » s'ajoutait aux autres lignes réservées et gonflait le total.
        lines = move.move_line_ids
        if lines:
            lines[:1].quantity = qty
            if lines[1:]:
                lines[1:].quantity = 0
        else:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'quantity': qty,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
            })
        # Quantité comptée par l'opérateur = quantité confirmée : sans
        # « picked », button_finish() (noyau mrp) écrase le comptage par la
        # consommation théorique de chaque move non pické.
        move.picked = True
        detail = self.sf_get_detail()
        detail['needs_lot'] = move.product_id.tracking != 'none'
        detail['over_demand'] = float_compare(
            qty, move.product_uom_qty, precision_rounding=move.product_uom.rounding) > 0
        return detail

    def sf_scan(self, barcode):
        """Résout un code-barres : composant de l'OT -> +1 UdM consommée."""
        self.ensure_one()
        move = self.move_raw_ids.filtered(lambda m: m.product_id.barcode == barcode)
        if move:
            move = move[0]
            new_qty = sum(move.move_line_ids.mapped('quantity')) + 1.0
            detail = self.sf_consume(move.id, new_qty)
            return {'found': True, 'action': 'consume', 'move_id': move.id, 'detail': detail}
        return {'found': False}
