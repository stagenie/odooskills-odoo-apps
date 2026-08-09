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
