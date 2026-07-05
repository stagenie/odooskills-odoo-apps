# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryNativeUserGuards(TransactionCase):
    """The module must stay behaviorally invisible to users without any
    treasury group (native accounting flows) — EXCEPT for the closing
    integrity locks, which must apply to everyone.

    Regression tests for the fail-open bug where a non-treasury user could
    silently cancel/reset a payment whose mirror cash operation belonged to
    a validated closing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash Native Guard', 'type': 'cash', 'code': 'TCNG1',
        })
        cls.cash = cls.env['oski.treasury.cash'].create({
            'name': 'Native Guard Cash', 'code': 'NGRD1',
            'journal_id': cls.journal_cash.id,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Native Guard Partner',
        })
        # Accounting rights, NO treasury group.
        cls.account_user = cls.env['res.users'].create({
            'name': 'Native Accountant',
            'login': 'native_accountant_guard',
            'email': 'native_accountant_guard@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('account.group_account_manager').id,
            ])],
        })

    def _payment_with_op(self):
        """A posted payment on the open cash journal: the mirror cash
        operation is auto-created (test env runs as superuser)."""
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer',
            'amount': 100.0, 'partner_id': self.partner.id,
            'journal_id': self.journal_cash.id,
        })
        payment.action_post()
        self.assertTrue(
            payment.treasury_operation_id,
            "posting on an open cash journal must create the mirror operation",
        )
        return payment

    def _validate_closing_with(self, op):
        closing = self.env['oski.treasury.cash.closing'].create({
            'cash_id': self.cash.id,
        })
        op.closing_id = closing.id
        closing.invalidate_recordset()
        closing.balance_end_real = closing.balance_end_theoretical
        closing.action_confirm()
        closing.action_validate()
        self.assertEqual(closing.state, 'validated')
        return closing

    def test_native_user_blocked_by_validated_closing(self):
        """A user without treasury access cannot cancel/reset a payment
        whose mirror operation is locked in a validated closing."""
        payment = self._payment_with_op()
        self._validate_closing_with(payment.treasury_operation_id)
        payment_as_user = payment.with_user(self.account_user)
        with self.assertRaises(UserError):
            payment_as_user.action_cancel()
        with self.assertRaises(UserError):
            payment_as_user.action_draft()

    def test_native_user_can_cancel_unlocked_payment(self):
        """A user without treasury access can cancel an unlocked payment,
        and the mirror operation is cancelled with it (no stale mirror)."""
        payment = self._payment_with_op()
        op = payment.treasury_operation_id
        payment.with_user(self.account_user).action_cancel()
        self.assertEqual(op.sudo().state, 'cancel')

    def test_native_user_can_draft_unlocked_payment(self):
        """A user without treasury access can reset an unlocked payment to
        draft, and the mirror operation follows (posted -> draft)."""
        payment = self._payment_with_op()
        op = payment.treasury_operation_id
        payment.with_user(self.account_user).action_draft()
        self.assertEqual(op.sudo().state, 'draft')
