# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryIntegration(TransactionCase):
    """Integration tests for the oski_treasury module (cash registers,
    operations, chained closings, safes and transfers with 3-level balance
    control)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dedicated journals (created, not reused: a cash register occupies a
        # journal exclusively -- UNIQUE(journal_id, company_id) -- so reusing
        # a journal already linked to an existing cash register would make
        # the tests fail).
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash Test', 'type': 'cash', 'code': 'TCSHI',
        })
        cls.journal_cash2 = cls.env['account.journal'].create({
            'name': 'Cash Test 2', 'type': 'cash', 'code': 'TCSI2',
        })
        # Category
        cls.category_in = cls.env.ref('oski_treasury.category_vente')
        cls.category_out = cls.env.ref('oski_treasury.category_achat')
        cls.category_ajust = cls.env.ref('oski_treasury.category_ajustement')

    # ========================
    # Cash register tests
    # ========================

    def test_01_create_cash(self):
        """Creating a cash register with an initial balance of 0"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Main Cash Register',
            'code': 'CP01',
            'journal_id': self.journal_cash.id,
        })
        self.assertEqual(cash.state, 'open')
        self.assertEqual(cash.current_balance, 0.0)
        self.assertTrue(cash.active)

    def test_02_unique_code(self):
        """The code must be unique per company"""
        self.env['oski.treasury.cash'].create({
            'name': 'Cash A', 'code': 'DUP1',
            'journal_id': self.journal_cash.id,
        })
        with self.assertRaises(Exception):
            self.env['oski.treasury.cash'].create({
                'name': 'Cash B', 'code': 'DUP1',
                'journal_id': self.journal_cash2.id,
            })

    def test_03_state_transitions(self):
        """Transitions: open -> closed -> locked -> open"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Trans', 'code': 'TR01',
            'journal_id': self.journal_cash.id,
        })
        cash.action_close_temporary()
        self.assertEqual(cash.state, 'closed')
        cash.action_lock()
        self.assertEqual(cash.state, 'locked')
        cash.action_open()
        self.assertEqual(cash.state, 'open')

    def test_04_max_amount_constraint(self):
        """max_amount cannot be negative"""
        with self.assertRaises(ValidationError):
            self.env['oski.treasury.cash'].create({
                'name': 'Cash Neg', 'code': 'NEG1',
                'journal_id': self.journal_cash.id,
                'max_amount': -100,
            })

    # ========================
    # Operation tests
    # ========================

    def test_10_operation_in_out(self):
        """In/out operations affect the balance"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Ops', 'code': 'OPS1',
            'journal_id': self.journal_cash.id,
        })
        # In
        op_in = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'in',
            'category_id': self.category_in.id,
            'amount': 10000,
        })
        op_in.action_post()
        cash.invalidate_recordset()
        self.assertEqual(cash.current_balance, 10000)

        # Out
        op_out = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'out',
            'category_id': self.category_out.id,
            'amount': 3000,
        })
        op_out.action_post()
        cash.invalidate_recordset()
        self.assertEqual(cash.current_balance, 7000)

    def test_11_operation_amount_positive(self):
        """The amount must be > 0"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Amt', 'code': 'AMT1',
            'journal_id': self.journal_cash.id,
        })
        with self.assertRaises(ValidationError):
            self.env['oski.treasury.cash.operation'].create({
                'cash_id': cash.id,
                'operation_type': 'in',
                'category_id': self.category_in.id,
                'amount': 0,
            })

    def test_12_operation_workflow(self):
        """Workflow: draft -> posted -> cancel -> draft"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash WF', 'code': 'WF01',
            'journal_id': self.journal_cash.id,
        })
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'in',
            'category_id': self.category_in.id,
            'amount': 5000,
        })
        self.assertEqual(op.state, 'draft')
        op.action_post()
        self.assertEqual(op.state, 'posted')
        op.action_cancel()
        self.assertEqual(op.state, 'cancel')
        op.action_draft()
        self.assertEqual(op.state, 'draft')

    def test_13_cannot_delete_posted(self):
        """Cannot delete a posted operation"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Del', 'code': 'DEL1',
            'journal_id': self.journal_cash.id,
        })
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'in',
            'category_id': self.category_in.id,
            'amount': 1000,
        })
        op.action_post()
        with self.assertRaises(UserError):
            op.unlink()

    def test_14_balance_check_on_out(self):
        """Out blocked if insufficient balance (control_level=blocking)"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Ctrl', 'code': 'CTR1',
            'journal_id': self.journal_cash.id,
            'control_level': 'blocking',
        })
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'out',
            'category_id': self.category_out.id,
            'amount': 5000,
        })
        with self.assertRaises(UserError):
            op.action_post()

    def test_15_sequence_generated(self):
        """The name is auto-generated by sequence"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Seq', 'code': 'SEQ1',
            'journal_id': self.journal_cash.id,
        })
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'in',
            'category_id': self.category_in.id,
            'amount': 100,
        })
        self.assertTrue(op.name.startswith('OPC/'))

    # ========================
    # Closing tests
    # ========================

    def test_20_closing_workflow(self):
        """Closing workflow: draft -> confirmed -> validated"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Cash Clot', 'code': 'CLT1',
            'journal_id': self.journal_cash.id,
        })
        # Add an operation
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id,
            'operation_type': 'in',
            'category_id': self.category_in.id,
            'amount': 20000,
        })
        op.action_post()

        # Create the closing
        closing = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id,
        })
        # Link the operation
        op.closing_id = closing.id
        closing.invalidate_recordset()

        self.assertEqual(closing.balance_start, 0.0)
        self.assertEqual(closing.total_in, 20000)
        self.assertEqual(closing.balance_end_theoretical, 20000)

        # Enter the actual balance
        closing.balance_end_real = 20000
        closing.action_confirm()
        self.assertEqual(closing.state, 'confirmed')

        closing.action_validate()
        self.assertEqual(closing.state, 'validated')
        # The cash register must be updated
        cash.invalidate_recordset()
        self.assertEqual(cash.last_closing_balance, 20000)

    def _fund_cash(self, cash, amount):
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': amount,
        })
        op.action_post()

    def test_51_balance_in_motion(self):
        """Balance in motion = posted ops of an ongoing closing."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashMotion', 'code': 'CMOT',
            'journal_id': self.journal_cash.id,
        })
        self._fund_cash(cash, 5000)  # no ongoing closing -> 0
        cash.invalidate_recordset()
        self.assertEqual(cash.balance_in_motion, 0.0)

        closing = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': fields.Date.today(),
        })
        # operation attached to the ongoing closing (auto-link on post)
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 1200,
        })
        op.action_post()
        cash.invalidate_recordset()
        self.assertEqual(op.closing_id, closing)
        self.assertEqual(cash.balance_in_motion, 1200.0)
        self.assertTrue(cash.has_pending_closing)

    def test_53_multiple_closings_same_day(self):
        """Two closings on the same day: the 2nd correctly loads its
        operations and its starting balance = actual balance of the 1st
        validated closing."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashMulti', 'code': 'CMUL',
            'journal_id': self.journal_cash.id,
        })
        today = fields.Date.today()
        # --- Closing 1 ---
        closing1 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': today,
        })
        op1 = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 10000,
        })
        op1.action_post()
        self.assertEqual(op1.closing_id, closing1)
        closing1.action_confirm()
        self.assertEqual(closing1.balance_start, 0.0)
        closing1.balance_end_real = closing1.balance_end_theoretical  # 10000
        closing1.action_validate()
        self.assertEqual(closing1.state, 'validated')
        cash.invalidate_recordset()
        self.assertEqual(cash.last_closing_balance, 10000)

        # --- Operation between the two closings (same day) ---
        op2 = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 5000,
        })
        op2.action_post()
        self.assertFalse(op2.closing_id, "No ongoing closing after validation")

        # --- Closing 2 (same day) ---
        closing2 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': today,
        })
        self.assertEqual(closing2.closing_number, 2)
        self.assertEqual(closing2.balance_start, 10000,
                         "Starting balance = actual balance of the last "
                         "validated closing")
        closing2.action_confirm()
        # The operation of the day must have been loaded (time.max filter regression)
        self.assertEqual(op2.closing_id, closing2)
        self.assertEqual(closing2.balance_start, 10000)
        self.assertEqual(closing2.total_in, 5000)
        self.assertEqual(closing2.balance_end_theoretical, 15000)

    def test_54_out_of_order_closing_chain(self):
        """Closing B confirmed BEFORE A is validated: its starting balance is
        re-frozen at validation on the actual balance of A."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashOOO', 'code': 'COOO',
            'journal_id': self.journal_cash.id,
        })
        today = fields.Date.today()
        closing_a = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': today,
        })
        op1 = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 10000,
        })
        op1.action_post()  # linked to A
        closing_a.action_confirm()
        closing_a.balance_end_real = closing_a.balance_end_theoretical  # 10000

        # B created AND confirmed BEFORE A is validated
        closing_b = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': today,
        })
        closing_b.action_confirm()
        self.assertEqual(closing_b.balance_start, 0.0, "A not yet validated")

        # A is now validated
        closing_a.action_validate()
        self.assertEqual(closing_a.state, 'validated')

        # B is validated: its starting balance must re-freeze on A (regression)
        closing_b.balance_end_real = 10000
        closing_b.action_validate()
        self.assertEqual(closing_b.balance_start, 10000,
                         "B's balance_start must reflect A's actual balance")

    def test_55_cancel_closing_releases_operations(self):
        """Cancelling a closing releases its operations for a future closing."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashRel', 'code': 'CREL',
            'journal_id': self.journal_cash.id,
        })
        closing1 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': fields.Date.today(),
        })
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 5000,
        })
        op.action_post()
        self.assertEqual(op.closing_id, closing1)
        closing1.action_confirm()
        closing1.action_cancel()
        self.assertFalse(op.closing_id, "operation released after cancellation")
        self.assertEqual(op.state, 'posted')

        closing2 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': fields.Date.today(),
        })
        closing2.action_confirm()
        self.assertEqual(op.closing_id, closing2)
        self.assertEqual(closing2.total_in, 5000)

    def test_56_closing_number_without_explicit_date(self):
        """closing_number must increment even if closing_date is not passed
        in vals (API/shell creation: the default is only applied by
        super().create(), after the number is computed)."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashNum', 'code': 'CNUM',
            'journal_id': self.journal_cash.id,
        })
        closing1 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id, 'closing_date': fields.Date.today(),
        })
        self.assertEqual(closing1.closing_number, 1)
        # Without explicit closing_date -> must take today's date and number 2
        closing2 = self.env['oski.treasury.cash.closing'].create({
            'cash_id': cash.id,
        })
        self.assertEqual(closing2.closing_date, fields.Date.today())
        self.assertEqual(closing2.closing_number, 2,
                         "closing_number not incremented when closing_date "
                         "is absent from vals")

    # ========================
    # Transfer tests (cash <-> cash)
    # ========================

    def test_40_transfer_cash_to_cash(self):
        """Cash -> cash transfer creates 2 automatic operations"""
        cash1 = self.env['oski.treasury.cash'].create({
            'name': 'Source', 'code': 'SRC1',
            'journal_id': self.journal_cash.id,
        })
        cash2 = self.env['oski.treasury.cash'].create({
            'name': 'Dest', 'code': 'DST1',
            'journal_id': self.journal_cash2.id,
        })
        # Fund the source
        op_in = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash1.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 15000,
        })
        op_in.action_post()

        # Transfer
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': cash1.id,
            'cash_to_id': cash2.id,
            'amount': 5000,
        })
        transfer.action_confirm()
        self.assertEqual(transfer.state, 'confirm')
        self.assertTrue(transfer.cash_operation_out_id)
        self.assertTrue(transfer.cash_operation_in_id)

        # Check balances
        cash1.invalidate_recordset()
        cash2.invalidate_recordset()
        self.assertEqual(cash1.current_balance, 10000)
        self.assertEqual(cash2.current_balance, 5000)

        transfer.action_done()
        self.assertEqual(transfer.state, 'done')

    def test_41_transfer_amount_positive(self):
        """Transfer amount > 0"""
        with self.assertRaises(ValidationError):
            self.env['oski.treasury.transfer'].create({
                'transfer_type': 'cash_to_cash',
                'cash_from_id': self.env['oski.treasury.cash'].create({
                    'name': 'X', 'code': 'X01',
                    'journal_id': self.journal_cash.id,
                }).id,
                'cash_to_id': self.env['oski.treasury.cash'].create({
                    'name': 'Y', 'code': 'Y01',
                    'journal_id': self.journal_cash2.id,
                }).id,
                'amount': -100,
            })

    def test_42_transfer_same_source_dest(self):
        """Source != Destination"""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'Self', 'code': 'SLF1',
            'journal_id': self.journal_cash.id,
        })
        with self.assertRaises(ValidationError):
            self.env['oski.treasury.transfer'].create({
                'transfer_type': 'cash_to_cash',
                'cash_from_id': cash.id,
                'cash_to_id': cash.id,
                'amount': 1000,
            })

    def test_43_transfer_cancel_reverses(self):
        """Cancelling a transfer cancels its linked operations"""
        cash1 = self.env['oski.treasury.cash'].create({
            'name': 'Src Cancel', 'code': 'SC01',
            'journal_id': self.journal_cash.id,
        })
        cash2 = self.env['oski.treasury.cash'].create({
            'name': 'Dst Cancel', 'code': 'DC01',
            'journal_id': self.journal_cash2.id,
        })
        # Fund
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash1.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 10000,
        })
        op.action_post()

        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': cash1.id, 'cash_to_id': cash2.id,
            'amount': 3000,
        })
        transfer.action_confirm()
        transfer.action_cancel()

        self.assertEqual(transfer.state, 'cancel')
        self.assertEqual(transfer.cash_operation_out_id.state, 'cancel')
        self.assertEqual(transfer.cash_operation_in_id.state, 'cancel')

    def test_52_transfer_blocked_from_locked_cash(self):
        """Transfer from a locked cash register -> blocked."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashLock', 'code': 'CLCK',
            'journal_id': self.journal_cash.id,
        })
        cash2 = self.env['oski.treasury.cash'].create({
            'name': 'CashLock2', 'code': 'CLK2',
            'journal_id': self.journal_cash2.id,
        })
        self._fund_cash(cash, 5000)
        cash.action_lock()
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': cash.id, 'cash_to_id': cash2.id, 'amount': 1000,
        })
        with self.assertRaises(UserError):
            transfer.action_confirm()

    def test_57_force_transfer_cash_source(self):
        """force_transfer must bypass the balance control all the way
        through: the cash-out leg (action_post) must not re-block."""
        cash_src = self.env['oski.treasury.cash'].create({
            'name': 'CashForceSrc', 'code': 'CFS1',
            'journal_id': self.journal_cash.id,
        })
        cash_dst = self.env['oski.treasury.cash'].create({
            'name': 'CashForceDst', 'code': 'CFD1',
            'journal_id': self.journal_cash2.id,
        })
        # Source at 100, forced transfer of 5000 (blocking control by default)
        op = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash_src.id, 'operation_type': 'in',
            'category_id': self.category_in.id, 'amount': 100,
        })
        op.action_post()
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash', 'amount': 5000,
            'cash_from_id': cash_src.id, 'cash_to_id': cash_dst.id,
            'force_transfer': True,
        })
        transfer.action_confirm()
        self.assertEqual(transfer.state, 'confirm')
        self.assertEqual(cash_src.current_balance, -4900)
        self.assertEqual(cash_dst.current_balance, 5000)
        # Without force: the same transfer is blocked
        transfer2 = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash', 'amount': 5000,
            'cash_from_id': cash_dst.id, 'cash_to_id': cash_src.id,
            'force_transfer': False,
        })
        transfer2.amount = 99999
        with self.assertRaises(UserError):
            transfer2.action_confirm()

    # ========================
    # Safe tests
    # ========================

    _safe_seq = 0

    def _make_safe(self, name=None, code=None, **vals):
        """Creates a safe with a responsible user. name/code default to an
        auto-incremented, test-run-unique value so callers (including the
        D3 tests) can omit them entirely.

        allow_negative_balance is not set by default, allowing the model's
        own default (False) to apply unless the caller passes it explicitly."""
        self.__class__._safe_seq += 1
        vals.setdefault('name', name or f'Safe Test {self._safe_seq}')
        vals.setdefault('code', code or f'SFX{self._safe_seq:03d}')
        vals.setdefault('responsible_ids', [(6, 0, [self.env.ref('base.user_admin').id])])
        return self.env['oski.treasury.safe'].create(vals)

    def _make_safe_op(self, safe, operation_type, amount, date=None, **vals):
        """Creates (draft) a safe operation. `date` accepts a 'YYYY-MM-DD'
        string (converted by the Datetime field) to control ordering in the
        D3 historical-balance tests."""
        vals.setdefault('safe_id', safe.id)
        vals.setdefault('operation_type', operation_type)
        vals.setdefault('amount', amount)
        vals.setdefault('description', 'Test operation')
        if date:
            vals['date'] = date
        return self.env['oski.treasury.safe.operation'].create(vals)

    def _fund_safe(self, safe, amount):
        op = self._make_safe_op(safe, 'initial', amount, description='init')
        op.action_confirm()
        op.action_done()

    def test_30_safe_create_and_init(self):
        """Creating a safe and initializing it"""
        safe = self._make_safe('Main Safe', 'CF01')
        self.assertEqual(safe.state, 'active')
        self.assertEqual(safe.current_balance, 0.0)

        # Initialize
        op = self._make_safe_op(safe, 'initial', 50000, description='Initial balance')
        op.action_confirm()
        op.action_done()
        safe.invalidate_recordset()
        self.assertTrue(safe.is_initialized)
        self.assertEqual(safe.current_balance, 50000)

    def test_31_safe_single_init(self):
        """Only one initialization per safe"""
        safe = self._make_safe('Init Safe', 'CI01')
        self._make_safe_op(safe, 'initial', 10000, description='Init 1')
        with self.assertRaises(ValidationError):
            self._make_safe_op(safe, 'initial', 20000, description='Init 2')

    # ========================
    # D3 - historical operation balances
    # ========================

    def test_d3_safe_balance_historical(self):
        """balance_before/balance_after reflect the safe's state strictly
        BEFORE each operation, not the safe's live current_balance."""
        safe = self._make_safe(allow_negative_balance=True)
        op1 = self._make_safe_op(safe, 'other_in', 100.0, date='2026-01-01')
        op2 = self._make_safe_op(safe, 'other_out', 30.0, date='2026-01-02')
        (op1 + op2).action_confirm()
        (op1 + op2).action_done()
        self.assertEqual(op2.balance_before, 100.0)
        self.assertEqual(op2.balance_after, 70.0)
        self.assertEqual(op1.balance_before, 0.0)  # not the current global balance

    def test_d3_safe_balance_matches_current(self):
        """Invariant: balance_after of the last done operation == the
        safe's current_balance."""
        safe = self._make_safe(allow_negative_balance=True)
        ops = [self._make_safe_op(safe, 'other_in', a) for a in (50.0, 20.0)]
        for o in ops:
            o.action_confirm()
            o.action_done()
        self.assertEqual(ops[-1].balance_after, safe.current_balance)

    # ========================
    # Transfer tests (cash <-> safe)
    # ========================

    def test_50_transfer_cash_safe_matrix(self):
        """cash->safe, safe->cash, safe->safe: no amount is lost."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashMat', 'code': 'CMAT',
            'journal_id': self.journal_cash.id,
        })
        safe1 = self._make_safe('SafeMat1', 'SMA1')
        safe2 = self._make_safe('SafeMat2', 'SMA2')
        self._fund_cash(cash, 10000)
        self._fund_safe(safe1, 8000)

        # cash -> safe (3000)
        t1 = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_safe',
            'cash_from_id': cash.id, 'safe_to_id': safe1.id, 'amount': 3000,
        })
        t1.action_confirm()
        cash.invalidate_recordset(); safe1.invalidate_recordset()
        self.assertEqual(cash.current_balance, 7000)
        self.assertEqual(safe1.current_balance, 11000)

        # safe -> cash (2000)
        t2 = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'safe_to_cash',
            'safe_from_id': safe1.id, 'cash_to_id': cash.id, 'amount': 2000,
        })
        t2.action_confirm()
        cash.invalidate_recordset(); safe1.invalidate_recordset()
        self.assertEqual(cash.current_balance, 9000)
        self.assertEqual(safe1.current_balance, 9000)

        # safe -> safe (4000)
        t3 = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'safe_to_safe',
            'safe_from_id': safe1.id, 'safe_to_id': safe2.id, 'amount': 4000,
        })
        t3.action_confirm()
        safe1.invalidate_recordset(); safe2.invalidate_recordset()
        self.assertEqual(safe1.current_balance, 5000)
        self.assertEqual(safe2.current_balance, 4000)

    def test_58_force_transfer_safe_source(self):
        """force_transfer with a safe source: the safe-out leg
        (action_confirm) must not re-block."""
        safe = self._make_safe('SafeForce', 'SFOR')
        cash_dst = self.env['oski.treasury.cash'].create({
            'name': 'CashSafeForce', 'code': 'CSF1',
            'journal_id': self.journal_cash.id,
        })
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'safe_to_cash', 'amount': 1000,
            'safe_from_id': safe.id, 'cash_to_id': cash_dst.id,
            'force_transfer': True,
        })
        transfer.action_confirm()
        self.assertEqual(transfer.state, 'confirm')
        self.assertEqual(safe.current_balance, -1000)
        self.assertEqual(cash_dst.current_balance, 1000)

    # ========================
    # Final review wave - closing-late cron
    # ========================

    def test_59_cron_update_days_since_closing(self):
        """days_since_closing / is_closing_late are stored computes that
        never refresh on their own with the passing of time: the daily
        cron must recompute them explicitly."""
        cash = self.env['oski.treasury.cash'].create({
            'name': 'CashCronClosing', 'code': 'CCRC',
            'journal_id': self.journal_cash.id,
            'require_closing': True,
            'auto_close_days': 5,
        })
        ten_days_ago = fields.Datetime.now() - timedelta(days=10)
        cash.write({'last_closing_date': ten_days_ago})
        self.env['oski.treasury.cash']._cron_update_days_since_closing()
        cash.invalidate_recordset()
        self.assertEqual(cash.days_since_closing, 10)
        self.assertTrue(cash.is_closing_late)
