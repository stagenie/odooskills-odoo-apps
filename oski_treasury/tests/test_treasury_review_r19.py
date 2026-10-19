# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryReviewR19(TransactionCase):
    """Regression tests of the R19 review (posted operations frozen,
    multi-currency entries, global settings vs. company, payment re-post,
    transfer legs)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash R19', 'type': 'cash', 'code': 'TR19A',
        })
        cls.journal_cash2 = cls.env['account.journal'].create({
            'name': 'Cash R19 bis', 'type': 'cash', 'code': 'TR19B',
        })

        def _acc(code, name, atype):
            return cls.env['account.account'].create({
                'code': code, 'name': name, 'account_type': atype,
                'company_ids': [(4, cls.company.id)],
            })
        cls.acc_cash = _acc('TR19C', 'R19 Cash', 'asset_cash')
        cls.acc_rev = _acc('TR19R', 'R19 Revenue', 'income')
        cls.acc_exp = _acc('TR19E', 'R19 Expense', 'expense')
        params = cls.env['ir.config_parameter'].sudo()
        params.set_bool('oski_treasury.account_move_enabled', True)
        params.set_int('oski_treasury.default_cash_account_id', cls.acc_cash.id)
        params.set_int('oski_treasury.default_revenue_account_id', cls.acc_rev.id)
        params.set_int('oski_treasury.default_expense_account_id', cls.acc_exp.id)
        params.set_int('oski_treasury.journal_id', None)

        cls.category_in = cls.env.ref('oski_treasury.category_vente')
        cls.cash = cls.env['oski.treasury.cash'].create({
            'name': 'R19 Cash', 'code': 'R19C',
            'journal_id': cls.journal_cash.id,
            'allow_negative_balance': True,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'R19 Partner'})

    def _op(self, amount, cash=None, otype='in'):
        return self.env['oski.treasury.cash.operation'].create({
            'cash_id': (cash or self.cash).id, 'operation_type': otype,
            'category_id': self.category_in.id, 'amount': amount,
        })

    # --- Posted operations are frozen ---

    def test_posted_operation_amount_frozen(self):
        op = self._op(100.0)
        op.action_post()
        # As a real (non-superuser) treasury manager.
        op = op.with_user(self.env.ref('base.user_admin'))
        with self.assertRaises(UserError):
            op.write({'amount': 999.0})
        with self.assertRaises(UserError):
            op.write({'operation_type': 'out'})
        # Rewriting the same value and editing free text stay allowed.
        op.write({'amount': 100.0, 'description': 'note'})
        self.assertEqual(op.amount, 100.0)
        # A draft operation stays editable.
        draft = self._op(50.0).with_user(self.env.ref('base.user_admin'))
        draft.write({'amount': 60.0})
        self.assertEqual(draft.amount, 60.0)

    # --- Multi-currency entry ---

    def test_foreign_currency_register_entry_converted(self):
        foreign = self.env['res.currency'].with_context(active_test=False).search(
            [('id', '!=', self.company.currency_id.id),
             ('name', 'in', ('EUR', 'USD', 'GBP'))], limit=1)
        foreign.active = True
        # Odoo 20: a rate dated D applies from D+1 (res_currency.py `name < date`).
        self.env['res.currency.rate'].create({
            'name': fields.Date.subtract(fields.Date.today(), days=1), 'rate': 2.0,
            'currency_id': foreign.id, 'company_id': self.company.id,
        })
        cash = self.env['oski.treasury.cash'].create({
            'name': 'R19 Foreign', 'code': 'R19F',
            'journal_id': self.journal_cash2.id,
            'currency_id': foreign.id,
        })
        op = self._op(100.0, cash=cash)
        op.action_post()
        debit_line = op.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertAlmostEqual(debit_line.debit, 50.0, 2,
                               "100 foreign at rate 2 = 50 in company currency")
        self.assertEqual(debit_line.currency_id, foreign)
        self.assertAlmostEqual(debit_line.amount_currency, 100.0, 2)

    # --- Global journal setting of another company ignored ---

    def test_global_journal_of_other_company_ignored(self):
        other = self.env['res.company'].create({'name': 'R19 Other Co'})
        journal_other = self.env['account.journal'].create({
            'name': 'R19 Misc Other', 'type': 'general', 'code': 'R19O',
            'company_id': other.id,
        })
        self.env['ir.config_parameter'].sudo().set_int(
            'oski_treasury.journal_id', journal_other.id)
        op = self._op(80.0)
        op.action_post()
        self.assertTrue(op.move_id)
        self.assertEqual(op.move_id.journal_id, self.journal_cash)

    # --- Payment re-posted after reset to draft ---

    def test_payment_repost_resyncs_mirror_operation(self):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer',
            'amount': 100.0, 'partner_id': self.partner.id,
            'journal_id': self.journal_cash.id,
        })
        payment.action_post()
        op = payment.treasury_operation_id
        self.assertEqual(op.state, 'posted')
        self.cash.invalidate_recordset()
        self.assertEqual(self.cash.current_balance, 100.0)

        payment.action_draft()
        self.assertEqual(op.state, 'draft')
        payment.amount = 130.0
        payment.action_post()
        self.assertEqual(payment.treasury_operation_id, op)
        self.assertEqual(op.state, 'posted',
                         "the mirror operation must follow the re-posted payment")
        self.assertEqual(op.amount, 130.0)
        self.cash.invalidate_recordset()
        self.assertEqual(self.cash.current_balance, 130.0)

    def test_payment_repost_after_cancel(self):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer',
            'amount': 40.0, 'partner_id': self.partner.id,
            'journal_id': self.journal_cash.id,
        })
        payment.action_post()
        op = payment.treasury_operation_id
        payment.action_cancel()
        self.assertEqual(op.state, 'cancel')
        payment.action_draft()
        payment.action_post()
        self.assertEqual(op.state, 'posted')
        self.cash.invalidate_recordset()
        self.assertEqual(self.cash.current_balance, 40.0)

    # --- Transfer legs ---

    def test_transfer_missing_destination_refused(self):
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_safe',
            'cash_from_id': self.cash.id, 'amount': 10.0,
        })
        with self.assertRaises(UserError):
            transfer.action_confirm()
        self.assertEqual(transfer.state, 'draft')

    def test_transfer_cross_currency_refused(self):
        foreign = self.env['res.currency'].with_context(active_test=False).search(
            [('id', '!=', self.company.currency_id.id),
             ('name', 'in', ('EUR', 'USD', 'GBP'))], limit=1)
        foreign.active = True
        cash_foreign = self.env['oski.treasury.cash'].create({
            'name': 'R19 Foreign Dst', 'code': 'R19FD',
            'journal_id': self.journal_cash2.id,
            'currency_id': foreign.id,
        })
        self._op(500.0).action_post()
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': self.cash.id, 'cash_to_id': cash_foreign.id,
            'amount': 100.0,
        })
        with self.assertRaises(UserError):
            transfer.action_confirm()
