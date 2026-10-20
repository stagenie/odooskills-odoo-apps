import json

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCompanyContext(HttpCase):
    """Les routes JSON agissent dans les sociétés COCHÉES du sélecteur.

    Le client envoie ``context.allowed_company_ids`` ; le serveur ne retient
    que les sociétés de l'utilisateur. Avant : contexte ignoré, l'opérateur
    multi-société qui a coché B voyait / scannait aussi les bons de A et
    tout ce qui dépend de ``env.company`` partait dans A."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref('base.main_company')
        cls.company_b = cls.env['res.company'].create({'name': 'Société B cochée'})
        cls.company_c = cls.env['res.company'].create({'name': 'Société C interdite'})
        cls.customers = cls.env.ref('stock.stock_location_customers')
        cls.product = cls.env['product.product'].create({
            'name': 'Article multi-société', 'is_storable': True,
            'barcode': 'OSKICOMP01', 'company_id': False})
        cls.picking_a = cls._delivery(cls.company_a)
        cls.picking_b = cls._delivery(cls.company_b)
        cls.picking_c = cls._delivery(cls.company_c)
        cls.operator = new_test_user(
            cls.env, login='oski_bc_mc', password='oski_bc_mc',
            groups='stock.group_stock_user',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, (cls.company_a | cls.company_b).ids)])

    @classmethod
    def _delivery(cls, company):
        wh = cls.env['stock.warehouse'].search(
            [('company_id', '=', company.id)], limit=1)
        cls.env['stock.quant']._update_available_quantity(
            cls.product, wh.lot_stock_id, 3)
        picking = cls.env['stock.picking'].with_company(company).create({
            'picking_type_id': wh.out_type_id.id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': cls.customers.id,
            'company_id': company.id,
            'move_ids': [(0, 0, {
                'name': cls.product.name, 'product_id': cls.product.id, 'product_uom_qty': 3,
                'product_uom': cls.product.uom_id.id,
                'location_id': wh.lot_stock_id.id,
                'location_dest_id': cls.customers.id,
                'company_id': company.id})],
        })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _call(self, route, company_ids, **params):
        params['context'] = {'allowed_company_ids': company_ids, 'lang': 'fr_FR'}
        r = self.url_open(
            f'/oski_stock_barcode/{route}',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                             'params': params}).encode(),
            headers={'Content-Type': 'application/json'})
        payload = json.loads(r.content)
        self.assertNotIn('error', payload, payload.get('error'))
        return payload['result']

    def _found(self, picking, company_ids):
        """Le scan du nom de ``picking`` rend-il CE bon ? (les entrepôts de
        sociétés créées en test peuvent partager un préfixe de séquence)."""
        res = self._call('scan_picking', company_ids, barcode=picking.name)
        return res['found'] and res['picking']['id'] == picking.id

    def test_checked_company_b_scopes_scan_and_validation(self):
        """B seule cochée : le bon de B est trouvé et validé, celui de A non."""
        self.authenticate('oski_bc_mc', 'oski_bc_mc')
        b = [self.company_b.id]
        self.assertTrue(self._found(self.picking_b, b))
        self.assertFalse(self._found(self.picking_a, b))
        listed = {p['id'] for p in self._call(
            'get_pickings', b, picking_type_code='outgoing')}
        self.assertIn(self.picking_b.id, listed)
        self.assertNotIn(self.picking_a.id, listed)
        res = self._call('update_line_qty', b, picking_id=self.picking_b.id,
                         product_id=self.product.id, qty=3)
        self.assertTrue(res.get('success'), res)
        res = self._call('validate_picking', b, picking_id=self.picking_b.id)
        self.assertTrue(res.get('success'), res)
        self.assertEqual(self.picking_b.state, 'done')
        # Le bon de A, hors sélection, n'est pas atteignable.
        res = self._call('get_picking_lines', b, picking_id=self.picking_a.id)
        self.assertIn('introuvable', res.get('error', ''))
        # A et B cochées : les deux sont visibles.
        self.assertTrue(self._found(self.picking_a, [self.company_a.id,
                                                     self.company_b.id]))

    def test_unauthorized_company_is_ignored(self):
        """Une société hors des sociétés de l'utilisateur est écartée sans
        erreur : jamais d'accès à ses bons, la sélection autorisée s'applique."""
        self.authenticate('oski_bc_mc', 'oski_bc_mc')
        forged = [self.company_c.id, self.company_b.id]
        self.assertFalse(self._found(self.picking_c, forged))
        self.assertTrue(self._found(self.picking_b, forged))
        self.assertFalse(self._found(self.picking_a, forged))
        res = self._call('get_picking_lines', forged,
                         picking_id=self.picking_c.id)
        self.assertIn('introuvable', res.get('error', ''))
        # Rien d'autorisé : comportement par défaut (sociétés de l'utilisateur).
        self.assertFalse(self._found(self.picking_c, [self.company_c.id]))
        self.assertTrue(self._found(self.picking_a, [self.company_c.id]))
