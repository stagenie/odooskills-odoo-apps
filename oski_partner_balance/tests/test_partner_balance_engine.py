from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'partner_balance')
class TestPartnerBalanceEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'PB Customer A'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'PB Customer B'})
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'PB Sales', 'type': 'sale', 'code': 'PBSAL',
        })
        cls.journal_sale2 = cls.env['account.journal'].create({
            'name': 'PB Sales 2', 'type': 'sale', 'code': 'PBSA2',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'PB Service', 'type': 'service', 'lst_price': 100.0,
        })

    @classmethod
    def _make_invoice(cls, partner, date, amount, journal=None, post=True,
                      operation_datetime=None, move_type='out_invoice'):
        """Create (and by default post) a one-line invoice."""
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner.id,
            'journal_id': (journal or cls.journal_sale).id,
            'invoice_date': date,
            'date': date,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [(6, 0, [])],
            })],
        })
        if operation_datetime:
            move.oski_operation_datetime = operation_datetime
        if post:
            move.action_post()
        return move

    def test_00_module_installed(self):
        """The module is installed and its state is 'installed'."""
        module = self.env['ir.module.module'].search(
            [('name', '=', 'oski_partner_balance')], limit=1)
        self.assertTrue(module, "module record not found")
        self.assertEqual(module.state, 'installed')

    def test_01_operation_datetime_default(self):
        """A new move gets a non-empty operation datetime."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal_sale.id,
            'invoice_date': '2026-01-15',
        })
        self.assertTrue(move.oski_operation_datetime)

    def test_02_exclude_flag_defaults_to_false(self):
        """Nothing is excluded from the balance unless someone ticks the box."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal_sale.id,
            'invoice_date': '2026-01-15',
        })
        self.assertFalse(move.oski_exclude_from_balance)

    def test_03_operation_datetime_is_writable(self):
        """An accountant can correct the operation datetime to order same-day moves."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal_sale.id,
            'invoice_date': '2026-01-15',
        })
        move.oski_operation_datetime = '2026-01-15 08:30:00'
        self.assertEqual(
            str(move.oski_operation_datetime), '2026-01-15 08:30:00')

    def _options(self, **kw):
        """Default option dict, overridable field by field."""
        options = {
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'include_opening': True,
            'partner_ids': [],
            'scope': 'receivable',
            'journal_filter': 'all',
            'journal_ids': [],
            'target_moves': 'posted',
        }
        options.update(kw)
        return options

    def test_10_sections_per_scope(self):
        engine = self.env['oski.partner.balance.engine']
        self.assertEqual(engine._sections('receivable'), ['receivable'])
        self.assertEqual(engine._sections('payable'), ['payable'])
        self.assertEqual(engine._sections('both'), ['receivable', 'payable'])
        self.assertEqual(engine._sections('net'), ['net'])

    def test_11_account_types_per_section(self):
        engine = self.env['oski.partner.balance.engine']
        self.assertEqual(engine._account_types('receivable'), ['asset_receivable'])
        self.assertEqual(engine._account_types('payable'), ['liability_payable'])
        self.assertEqual(
            engine._account_types('net'),
            ['asset_receivable', 'liability_payable'])

    def test_12_base_domain_excludes_flagged_moves(self):
        engine = self.env['oski.partner.balance.engine']
        domain = engine._base_domain(self._options(), 'receivable')
        self.assertIn(('move_id.oski_exclude_from_balance', '=', False), domain)
        self.assertIn(('parent_state', '=', 'posted'), domain)
        self.assertIn(('partner_id', '!=', False), domain)

    def test_13_base_domain_target_moves_all(self):
        engine = self.env['oski.partner.balance.engine']
        domain = engine._base_domain(self._options(target_moves='all'), 'receivable')
        self.assertIn(('parent_state', 'in', ('draft', 'posted')), domain)

    def test_14_base_domain_journal_include_and_exclude(self):
        engine = self.env['oski.partner.balance.engine']
        jid = self.journal_sale.id
        included = engine._base_domain(
            self._options(journal_filter='include', journal_ids=[jid]), 'receivable')
        self.assertIn(('journal_id', 'in', [jid]), included)
        excluded = engine._base_domain(
            self._options(journal_filter='exclude', journal_ids=[jid]), 'receivable')
        self.assertIn(('journal_id', 'not in', [jid]), excluded)

    def test_15_base_domain_ignores_empty_journal_list(self):
        """Choosing 'include' without picking a journal must not empty the report."""
        engine = self.env['oski.partner.balance.engine']
        domain = engine._base_domain(
            self._options(journal_filter='include', journal_ids=[]), 'receivable')
        self.assertFalse([leaf for leaf in domain if leaf[0] == 'journal_id'])

    def test_20_opening_balance_sums_lines_before_date_from(self):
        partner = self.env['res.partner'].create({'name': 'PB Opening 1'})
        self._make_invoice(partner, '2025-11-10', 300.0)
        self._make_invoice(partner, '2025-12-05', 200.0)
        self._make_invoice(partner, '2026-03-01', 50.0)
        openings = self.env['oski.partner.balance.engine']._opening_balances(
            self._options(partner_ids=[partner.id]), 'receivable')
        self.assertAlmostEqual(openings.get(partner.id, 0.0), 500.0, places=2)

    def test_21_opening_balance_ignores_excluded_moves(self):
        partner = self.env['res.partner'].create({'name': 'PB Opening 2'})
        self._make_invoice(partner, '2025-11-10', 300.0)
        excluded = self._make_invoice(partner, '2025-12-05', 200.0)
        excluded.oski_exclude_from_balance = True
        openings = self.env['oski.partner.balance.engine']._opening_balances(
            self._options(partner_ids=[partner.id]), 'receivable')
        self.assertAlmostEqual(openings.get(partner.id, 0.0), 300.0, places=2)

    def test_22_opening_balance_is_empty_without_prior_lines(self):
        partner = self.env['res.partner'].create({'name': 'PB Opening 3'})
        self._make_invoice(partner, '2026-03-01', 120.0)
        openings = self.env['oski.partner.balance.engine']._opening_balances(
            self._options(partner_ids=[partner.id]), 'receivable')
        self.assertEqual(openings.get(partner.id, 0.0), 0.0)

    def test_23_opening_balance_respects_journal_filter(self):
        partner = self.env['res.partner'].create({'name': 'PB Opening 4'})
        self._make_invoice(partner, '2025-11-10', 300.0, journal=self.journal_sale)
        self._make_invoice(partner, '2025-11-11', 400.0, journal=self.journal_sale2)
        openings = self.env['oski.partner.balance.engine']._opening_balances(
            self._options(partner_ids=[partner.id], journal_filter='exclude',
                          journal_ids=[self.journal_sale2.id]), 'receivable')
        self.assertAlmostEqual(openings.get(partner.id, 0.0), 300.0, places=2)

    def test_24_line_on_date_from_belongs_to_the_period(self):
        """Strictly before: a line dated exactly on date_from is NOT an opening."""
        partner = self.env['res.partner'].create({'name': 'PB Opening 5'})
        self._make_invoice(partner, '2025-12-20', 150.0)
        self._make_invoice(partner, '2026-01-01', 90.0)
        openings = self.env['oski.partner.balance.engine']._opening_balances(
            self._options(partner_ids=[partner.id]), 'receivable')
        self.assertAlmostEqual(
            openings.get(partner.id, 0.0), 150.0, places=2,
            msg="the line dated on date_from must belong to the period, "
                "not to the opening balance")
