# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryAccounting(TransactionCase):
    """Accounting entries of cash operations (configurable + anti-duplication)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        # Dedicated journals (created, not reused -- a cash register occupies
        # a journal exclusively, see UNIQUE(journal_id, company_id)).
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash Test Accounting', 'type': 'cash', 'code': 'TCSHA',
        })
        cls.journal_bank = cls.env['account.journal'].create({
            'name': 'Bank Test Accounting', 'type': 'bank', 'code': 'TBNKA',
        })

        def _acc(code, name, atype):
            return cls.env['account.account'].create({
                'code': code, 'name': name, 'account_type': atype,
                'company_ids': [(4, company.id)],
            })
        cls.acc_cash = _acc('TCASH1', 'Treasury Cash', 'asset_cash')
        cls.acc_rev = _acc('TREV1', 'Treasury Revenue', 'income')
        cls.acc_exp = _acc('TEXP1', 'Treasury Expense', 'expense')
        cls.acc_transit = _acc('TTRA1', 'Internal Transfer', 'asset_current')

        params = cls.env['ir.config_parameter'].sudo()
        params.set_param('oski_treasury.account_move_enabled', 'True')
        params.set_param('oski_treasury.default_cash_account_id', str(cls.acc_cash.id))
        params.set_param('oski_treasury.default_revenue_account_id', str(cls.acc_rev.id))
        params.set_param('oski_treasury.default_expense_account_id', str(cls.acc_exp.id))
        params.set_param('oski_treasury.default_transfer_account_id', str(cls.acc_transit.id))

        cls.category_in = cls.env.ref('oski_treasury.category_vente')
        cls.category_out = cls.env.ref('oski_treasury.category_achat')
        cls.cash = cls.env['oski.treasury.cash'].create({
            'name': 'Accounting Cash', 'code': 'CCPT',
            'journal_id': cls.journal_cash.id,
            'allow_negative_balance': True,  # entry tests, not balance control
        })

    def _op(self, otype, amount, category):
        return self.env['oski.treasury.cash.operation'].create({
            'cash_id': self.cash.id, 'operation_type': otype,
            'category_id': category.id, 'amount': amount,
        })

    def test_01_move_created_on_post_in(self):
        op = self._op('in', 1000.0, self.category_in)
        op.action_post()
        self.assertTrue(op.move_id, "An entry must be created")
        self.assertEqual(op.move_id.state, 'posted')
        self.assertEqual(sum(op.move_id.line_ids.mapped('debit')),
                         sum(op.move_id.line_ids.mapped('credit')))
        debit_line = op.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = op.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, self.acc_cash)
        self.assertEqual(credit_line.account_id, self.acc_rev)
        self.assertEqual(debit_line.debit, 1000.0)

    def test_02_move_created_on_post_out(self):
        op = self._op('out', 400.0, self.category_out)
        op.action_post()
        debit_line = op.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = op.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, self.acc_exp)
        self.assertEqual(credit_line.account_id, self.acc_cash)

    def test_03_category_account_override(self):
        special = self.env['oski.treasury.operation.category'].create({
            'name': 'Special Category', 'code': 'CATSPE', 'operation_type': 'in',
            'debit_account_id': self.acc_cash.id,
            'credit_account_id': self.acc_exp.id,
        })
        op = self._op('in', 250.0, special)
        op.action_post()
        debit_line = op.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = op.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, self.acc_cash)
        self.assertEqual(credit_line.account_id, self.acc_exp)

    def test_04_no_double_move_for_payment(self):
        """Operation linked to a payment: link to the native move, no re-creation."""
        partner = self.env['res.partner'].create({'name': 'Test Customer'})
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer',
            'amount': 700.0, 'partner_id': partner.id,
            'journal_id': self.journal_bank.id,
        })
        payment.action_post()
        self.assertTrue(payment.move_id)
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': self.cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 700.0,
            'payment_id': payment.id, 'is_manual': False,
        })
        op.action_post()
        self.assertEqual(op.move_id, payment.move_id,
                         "The operation must point to the payment's native move")

    def test_05_feature_disabled(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'oski_treasury.account_move_enabled', 'False')
        op = self._op('in', 100.0, self.category_in)
        op.action_post()
        self.assertFalse(op.move_id)
        # Restore for the other tests
        self.env['ir.config_parameter'].sudo().set_param(
            'oski_treasury.account_move_enabled', 'True')

    def test_06_move_removed_on_cancel(self):
        op = self._op('in', 300.0, self.category_in)
        op.action_post()
        move = op.move_id
        self.assertTrue(move.exists())
        op.action_cancel()
        self.assertFalse(op.move_id)
        self.assertFalse(move.exists())

    def test_07_transfer_op_no_move(self):
        """Transfer (internal) operations do not generate a GL entry."""
        journal_cash2 = self.env['account.journal'].create({
            'name': 'Accounting Cash 2', 'type': 'cash', 'code': 'CSC2',
        })
        cash2 = self.env['oski.treasury.cash'].create({
            'name': 'Accounting Cash Dst', 'code': 'CCP2',
            'journal_id': journal_cash2.id, 'allow_negative_balance': True,
        })
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': self.cash.id, 'cash_to_id': cash2.id, 'amount': 100.0,
        })
        transfer.action_confirm()
        self.assertFalse(transfer.cash_operation_out_id.move_id)
        self.assertFalse(transfer.cash_operation_in_id.move_id)

    def test_08_both_category_uses_directional_defaults(self):
        """'Both' category with fixed accounts: ignored in favor of the default
        accounts, which apply the correct direction according to operation_type."""
        both = self.env['oski.treasury.operation.category'].create({
            'name': 'Both Category', 'code': 'CATBOTH', 'operation_type': 'both',
            'debit_account_id': self.acc_rev.id,
            'credit_account_id': self.acc_exp.id,
        })
        op = self._op('out', 150.0, both)
        op.action_post()
        debit_line = op.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = op.move_id.line_ids.filtered(lambda l: l.credit > 0)
        # out -> debit expense, credit cash (NOT the category's fixed pair)
        self.assertEqual(debit_line.account_id, self.acc_exp)
        self.assertEqual(credit_line.account_id, self.acc_cash)

    def test_09_stale_account_non_blocking(self):
        """Stale default account (deleted id): no entry, no crash."""
        params = self.env['ir.config_parameter'].sudo()
        saved = params.get_param('oski_treasury.default_cash_account_id')
        params.set_param('oski_treasury.default_cash_account_id', '999999999')
        op = self._op('in', 120.0, self.category_in)
        op.action_post()  # must NOT raise
        self.assertEqual(op.state, 'posted')
        self.assertFalse(op.move_id)
        params.set_param('oski_treasury.default_cash_account_id', saved or '')
