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

    def test_30_rows_start_with_opening_line(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 1'})
        self._make_invoice(partner, '2025-12-01', 100.0)
        self._make_invoice(partner, '2026-02-01', 40.0)
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id]))
        self.assertTrue(rows[0]['is_opening'])
        self.assertAlmostEqual(rows[0]['cumulative'], 100.0, places=2)
        self.assertAlmostEqual(rows[1]['cumulative'], 140.0, places=2)

    def test_31_opening_can_be_switched_off(self):
        """Same moves, opening off: the final cumulative differs by the opening."""
        partner = self.env['res.partner'].create({'name': 'PB Rows 2'})
        self._make_invoice(partner, '2025-12-01', 100.0)
        self._make_invoice(partner, '2026-02-01', 40.0)
        engine = self.env['oski.partner.balance.engine']
        with_opening = engine._build_rows(
            self._options(partner_ids=[partner.id], include_opening=True))
        without = engine._build_rows(
            self._options(partner_ids=[partner.id], include_opening=False))
        self.assertFalse(any(row['is_opening'] for row in without))
        self.assertAlmostEqual(with_opening[-1]['cumulative'], 140.0, places=2)
        self.assertAlmostEqual(without[-1]['cumulative'], 40.0, places=2)

    def test_32_same_day_moves_ordered_by_operation_datetime(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 3'})
        late = self._make_invoice(partner, '2026-02-10', 70.0,
                                  operation_datetime='2026-02-10 17:00:00')
        early = self._make_invoice(partner, '2026-02-10', 30.0,
                                   operation_datetime='2026-02-10 08:00:00')
        rows = [r for r in self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id], include_opening=False))]
        self.assertEqual(rows[0]['move_id'], early.id)
        self.assertEqual(rows[1]['move_id'], late.id)
        self.assertAlmostEqual(rows[0]['cumulative'], 30.0, places=2)
        self.assertAlmostEqual(rows[1]['cumulative'], 100.0, places=2)

    def test_33_identical_datetimes_are_broken_by_id(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 4'})
        first = self._make_invoice(partner, '2026-02-11', 10.0,
                                   operation_datetime='2026-02-11 09:00:00')
        second = self._make_invoice(partner, '2026-02-11', 20.0,
                                    operation_datetime='2026-02-11 09:00:00')
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id], include_opening=False))
        self.assertEqual([r['move_id'] for r in rows], [first.id, second.id])

    def test_34_sequence_is_strictly_increasing(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 5'})
        self._make_invoice(partner, '2026-02-01', 10.0)
        self._make_invoice(partner, '2026-02-02', 20.0)
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id]))
        sequences = [row['sequence'] for row in rows]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(len(set(sequences)), len(sequences))

    def test_35_excluded_move_leaves_the_statement(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 6'})
        self._make_invoice(partner, '2026-02-01', 10.0)
        dropped = self._make_invoice(partner, '2026-02-02', 20.0)
        dropped.oski_exclude_from_balance = True
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id], include_opening=False))
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[-1]['cumulative'], 10.0, places=2)

    def test_36_scope_both_yields_two_sections(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 7'})
        journal_purchase = self.env['account.journal'].create({
            'name': 'PB Purchases', 'type': 'purchase', 'code': 'PBPUR',
        })
        self._make_invoice(partner, '2026-02-01', 100.0)
        self._make_invoice(partner, '2026-02-02', 60.0, journal=journal_purchase,
                           move_type='in_invoice')
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id], scope='both',
                          include_opening=False))
        self.assertEqual(
            {row['section'] for row in rows}, {'receivable', 'payable'})

    def test_37_scope_net_yields_one_running_balance(self):
        """Customer 100, vendor 60: the net cumulative ends at 40."""
        partner = self.env['res.partner'].create({'name': 'PB Rows 8'})
        journal_purchase = self.env['account.journal'].create({
            'name': 'PB Purchases 2', 'type': 'purchase', 'code': 'PBPU2',
        })
        self._make_invoice(partner, '2026-02-01', 100.0)
        self._make_invoice(partner, '2026-02-02', 60.0, journal=journal_purchase,
                           move_type='in_invoice')
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id], scope='net',
                          include_opening=False))
        self.assertEqual({row['section'] for row in rows}, {'net'})
        self.assertAlmostEqual(rows[-1]['cumulative'], 40.0, places=2)

    def test_38_partner_without_lines_and_without_opening_is_skipped(self):
        partner = self.env['res.partner'].create({'name': 'PB Rows 9'})
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner.id]))
        self.assertEqual(rows, [])

    def test_39_sequence_spans_partners_and_sections(self):
        """One counter for the whole result: no reset per partner or per section."""
        partner_a = self.env['res.partner'].create({'name': 'PB Rows 10 A'})
        partner_b = self.env['res.partner'].create({'name': 'PB Rows 10 B'})
        journal_purchase = self.env['account.journal'].create({
            'name': 'PB Purchases 3', 'type': 'purchase', 'code': 'PBPU3',
        })
        for partner in (partner_a, partner_b):
            self._make_invoice(partner, '2026-02-01', 100.0)
            self._make_invoice(partner, '2026-02-02', 60.0,
                               journal=journal_purchase, move_type='in_invoice')
        rows = self.env['oski.partner.balance.engine']._build_rows(
            self._options(partner_ids=[partner_a.id, partner_b.id],
                          scope='both', include_opening=False))
        sequences = [row['sequence'] for row in rows]
        self.assertEqual(len(rows), 4, "two partners x two sections x one line each")
        self.assertEqual(
            sequences, list(range(1, len(rows) + 1)),
            "the sequence must run 1..N across every section and partner; "
            "a counter reset per partner or per section would repeat values")
