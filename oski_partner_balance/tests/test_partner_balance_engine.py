from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'partner_balance')
class TestPartnerBalanceEngine(TransactionCase):

    def test_00_module_installed(self):
        """The module is installed and its state is 'installed'."""
        module = self.env['ir.module.module'].search(
            [('name', '=', 'oski_partner_balance')], limit=1)
        self.assertTrue(module, "module record not found")
        self.assertEqual(module.state, 'installed')
