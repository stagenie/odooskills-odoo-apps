from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'partner_balance')
class TestPartnerBalanceEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'PB Customer A'})
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'PB Sales', 'type': 'sale', 'code': 'PBSAL',
        })

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
