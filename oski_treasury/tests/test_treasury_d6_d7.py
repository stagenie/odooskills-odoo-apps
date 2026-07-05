# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryD6D7(TransactionCase):
    """D6 (dynamic menu visibility) and D7 (protected reset to draft) tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dedicated journals (created, not reused: a cash register occupies a
        # journal exclusively -- UNIQUE(journal_id, company_id)).
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash D6D7', 'type': 'cash', 'code': 'TD6D7',
        })
        cls.journal_cash2 = cls.env['account.journal'].create({
            'name': 'Cash D6D7 2', 'type': 'cash', 'code': 'TD6D8',
        })
        cls.journal_bank = cls.env['account.journal'].create({
            'name': 'Bank D6D7', 'type': 'bank', 'code': 'TBD6D7',
        })
        cls.category_in = cls.env.ref('oski_treasury.category_vente')
        cls.cash = cls.env['oski.treasury.cash'].create({
            'name': 'D6D7 Cash', 'code': 'D6D71',
            'journal_id': cls.journal_cash.id,
        })
        cls.cash2 = cls.env['oski.treasury.cash'].create({
            'name': 'D6D7 Cash 2', 'code': 'D6D72',
            'journal_id': cls.journal_cash2.id,
        })

    # ========================
    # Helpers
    # ========================

    _user_seq = 0

    def _make_user(self, groups):
        """Creates a user with the given group xmlid (implied groups, e.g.
        base.group_user via group_treasury_user, are added automatically)."""
        self.__class__._user_seq += 1
        n = self._user_seq
        group = self.env.ref(groups)
        return self.env['res.users'].create({
            'name': f'D6D7 User {n}',
            'login': f'd6d7_user_{n}',
            'email': f'd6d7_user_{n}@example.com',
            'group_ids': [(6, 0, [group.id])],
        })

    def _make_op(self, cash, operation_type, amount):
        return self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': operation_type,
            'category_id': self.category_in.id, 'amount': amount,
        })

    def _op_from_payment(self):
        """A cash operation created from an account.payment (payment_id set)."""
        partner = self.env['res.partner'].create({'name': 'D6D7 Partner'})
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer',
            'amount': 500.0, 'partner_id': partner.id,
            'journal_id': self.journal_bank.id,
        })
        payment.action_post()
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': self.cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 500.0,
            'payment_id': payment.id, 'is_manual': False,
        })
        op.action_post()
        return op

    def _make_transfer(self, transfer_type, cash_from, cash_to, amount):
        return self.env['oski.treasury.transfer'].create({
            'transfer_type': transfer_type,
            'cash_from_id': cash_from.id, 'cash_to_id': cash_to.id,
            'amount': amount,
        })

    def _validate_closing(self, closing):
        closing.action_confirm()
        closing.balance_end_real = closing.balance_end_theoretical
        closing.action_validate()

    # ========================
    # D6 - dynamic menu visibility
    # ========================

    def test_d6_menu_hidden_without_cash(self):
        """A treasury user with no cash register/safe assigned does not see
        the Cash Registers / Safes menus (structurally accessible via model
        access, but hidden dynamically by has_treasury_cash/safe)."""
        user = self._make_user('oski_treasury.group_treasury_user')
        menus = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
        self.assertNotIn(self.env.ref('oski_treasury.menu_treasury_cash').id, menus)
        self.assertNotIn(self.env.ref('oski_treasury.menu_treasury_safe').id, menus)

    def test_d6_menu_visible_with_cash(self):
        """Once assigned to a cash register, the user sees the menu."""
        user = self._make_user('oski_treasury.group_treasury_user')
        self.cash.user_ids = [(4, user.id)]
        menus = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
        self.assertIn(self.env.ref('oski_treasury.menu_treasury_cash').id, menus)

    def test_d6_manager_sees_all(self):
        """A treasury manager always sees both menus, cash/safe or not."""
        mgr = self._make_user('oski_treasury.group_treasury_manager')
        menus = self.env['ir.ui.menu'].with_user(mgr)._visible_menu_ids()
        self.assertIn(self.env.ref('oski_treasury.menu_treasury_cash').id, menus)
        self.assertIn(self.env.ref('oski_treasury.menu_treasury_safe').id, menus)

    # ========================
    # D7 - protected reset to draft
    # ========================

    def test_d7_reset_ok(self):
        """A plain posted operation (no payment/transfer, no validated
        closing) can be reset to draft and is detached from its closing."""
        op = self._make_op(self.cash, 'in', 50.0)
        op.action_post()
        self.assertTrue(op.can_reset_to_draft)
        op.action_reset_to_draft()
        self.assertEqual(op.state, 'draft')
        self.assertFalse(op.closing_id)

    def test_d7_reset_refused_payment(self):
        """An operation linked to a payment cannot be reset to draft."""
        op = self._op_from_payment()
        self.assertFalse(op.can_reset_to_draft)
        with self.assertRaises(UserError):
            op.action_reset_to_draft()

    def test_d7_reset_refused_validated_closing(self):
        """An operation belonging to a validated closing cannot be reset."""
        closing = self.env['oski.treasury.cash.closing'].create({'cash_id': self.cash.id})
        op = self._make_op(self.cash, 'in', 50.0)
        op.action_post()
        self.assertEqual(op.closing_id, closing)
        self._validate_closing(closing)
        self.assertFalse(op.can_reset_to_draft)
        with self.assertRaises(UserError):
            op.action_reset_to_draft()

    def test_d7_reset_refused_transfer(self):
        """An operation created by a transfer cannot be reset individually."""
        funding = self._make_op(self.cash, 'in', 100.0)
        funding.action_post()
        transfer = self._make_transfer('cash_to_cash', self.cash, self.cash2, 10.0)
        transfer.action_confirm()
        op = transfer.cash_operation_out_id
        self.assertTrue(op)
        self.assertFalse(op.can_reset_to_draft)
        with self.assertRaises(UserError):
            op.action_reset_to_draft()
