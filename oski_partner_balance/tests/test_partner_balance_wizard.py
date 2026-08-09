from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'partner_balance')
class TestPartnerBalanceWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'PBW Customer'})
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'PBW Sales', 'type': 'sale', 'code': 'PBWSA',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'PBW Service', 'type': 'service', 'lst_price': 100.0,
        })
        for date, amount in [('2025-12-01', 100.0), ('2026-02-01', 40.0)]:
            move = cls.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner.id,
                'journal_id': cls.journal_sale.id,
                'invoice_date': date,
                'date': date,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product.id,
                    'quantity': 1,
                    'price_unit': amount,
                    'tax_ids': [(6, 0, [])],
                })],
            })
            move.action_post()

    def _wizard(self, **kw):
        values = {
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'partner_ids': [(6, 0, [self.partner.id])],
        }
        values.update(kw)
        return self.env['oski.partner.balance.wizard'].create(values)

    def test_40_defaults(self):
        wizard = self._wizard()
        self.assertTrue(wizard.include_opening)
        self.assertEqual(wizard.scope, 'receivable')
        self.assertEqual(wizard.journal_filter, 'all')
        self.assertEqual(wizard.target_moves, 'posted')

    def test_41_generate_lines_materialises_rows(self):
        wizard = self._wizard()
        lines = wizard._generate_lines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].is_opening)
        self.assertAlmostEqual(lines[0].cumulative, 100.0, places=2)
        self.assertAlmostEqual(lines[1].cumulative, 140.0, places=2)

    def test_42_lines_are_ordered_by_sequence(self):
        wizard = self._wizard()
        wizard._generate_lines()
        lines = self.env['oski.partner.balance.line'].search(
            [('wizard_id', '=', wizard.id)])
        self.assertEqual([line.sequence for line in lines], [1, 2])

    def test_43_regenerating_replaces_previous_lines(self):
        wizard = self._wizard()
        wizard._generate_lines()
        wizard._generate_lines()
        lines = self.env['oski.partner.balance.line'].search(
            [('wizard_id', '=', wizard.id)])
        self.assertEqual(len(lines), 2, "old lines were not cleared")

    def test_44_action_returns_a_window_on_the_lines(self):
        wizard = self._wizard()
        action = wizard.action_view_lines()
        self.assertEqual(action['res_model'], 'oski.partner.balance.line')
        self.assertEqual(action['view_mode'], 'list')
        self.assertIn(('wizard_id', '=', wizard.id), action['domain'])

    def test_45_is_excluded_reflects_the_move_flag(self):
        wizard = self._wizard()
        lines = wizard._generate_lines()
        posting = lines.filtered(lambda line: not line.is_opening)
        self.assertFalse(posting.is_excluded)
        posting.move_id.oski_exclude_from_balance = True
        # `is_excluded` is a related field on a TransientModel: the ORM
        # registers no recompute trigger from account.move onto it, so the
        # value cached earlier in this same transaction is stale. A real
        # client never sees this — each RPC gets a fresh cache — but a test
        # that reads, writes and re-reads in one transaction must invalidate.
        posting.invalidate_recordset(['is_excluded'])
        self.assertTrue(posting.is_excluded)

    def test_46_plain_user_cannot_read_the_lines(self):
        """A user with no accounting group must not read partner balances."""
        user = self.env['res.users'].create({
            'name': 'PBW Plain', 'login': 'pbw_plain',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        wizard = self._wizard()
        wizard._generate_lines()
        with self.assertRaises(AccessError):
            self.env['oski.partner.balance.line'].with_user(user).search(
                [('wizard_id', '=', wizard.id)]).mapped('cumulative')

    def test_50_views_render(self):
        """Both views compile: a malformed arch fails here, not at the customer's."""
        self.env['oski.partner.balance.wizard'].get_view(
            self.env.ref('oski_partner_balance.view_partner_balance_wizard_form').id,
            'form')
        self.env['oski.partner.balance.line'].get_view(
            self.env.ref('oski_partner_balance.view_partner_balance_line_list').id,
            'list')

    def test_51_action_is_reachable(self):
        action = self.env.ref('oski_partner_balance.action_partner_balance_wizard')
        self.assertEqual(action.res_model, 'oski.partner.balance.wizard')
        self.assertEqual(action.target, 'new')

    def test_52_line_drills_down_to_its_document(self):
        """An accountant who spots an odd figure must reach the document."""
        wizard = self._wizard()
        lines = wizard._generate_lines()
        posting = lines.filtered(lambda line: not line.is_opening)[0]
        action = posting.action_open_move()
        self.assertEqual(action['res_model'], 'account.move')
        self.assertEqual(action['res_id'], posting.move_id.id)
        self.assertEqual(action['view_mode'], 'form')

    def test_60_pdf_renders(self):
        """The PDF renders end to end and starts with the %PDF marker."""
        wizard = self._wizard()
        wizard._generate_lines()
        report = self.env.ref('oski_partner_balance.action_report_partner_balance')
        with self.allow_pdf_render():
            pdf, content_type = report.with_context(
                force_report_rendering=True)._render_qweb_pdf(
                'oski_partner_balance.report_partner_balance', res_ids=wizard.ids)
        self.assertEqual(content_type, 'pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))
