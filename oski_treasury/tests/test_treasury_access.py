# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, ValidationError


@tagged('post_install', '-at_install', 'treasury')
class TestTreasuryAccess(TransactionCase):
    """Access control: a user only sees the cash registers/safes they are
    authorized on (user_ids/responsible), and only within their own
    company/companies (D2 hardening -- Task 8)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dedicated journals (created, not reused: a cash register occupies a
        # journal exclusively -- UNIQUE(journal_id, company_id)).
        cls.journal_cash = cls.env['account.journal'].create({
            'name': 'Cash ACL', 'type': 'cash', 'code': 'TACL1',
        })
        group_user = cls.env.ref('oski_treasury.group_treasury_user')
        cls.user_a = cls.env['res.users'].create({
            'name': 'Treasurer A', 'login': 'treso_a_acl',
            'email': 'treso_a_acl@example.com',
            'group_ids': [(6, 0, [group_user.id])],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'Treasurer B', 'login': 'treso_b_acl',
            'email': 'treso_b_acl@example.com',
            'group_ids': [(6, 0, [group_user.id])],
        })
        # Cash register authorized for A only
        cls.cash_a = cls.env['oski.treasury.cash'].create({
            'name': 'Cash A', 'code': 'ACLA',
            'journal_id': cls.journal_cash.id,
            'user_ids': [(6, 0, [cls.user_a.id])],
        })
        # Safe authorized for A only (via user_ids consultation)
        cls.safe_a = cls.env['oski.treasury.safe'].create({
            'name': 'Safe A', 'code': 'SACLA',
            'responsible_ids': [(6, 0, [cls.env.ref('base.user_admin').id])],
            'user_ids': [(6, 0, [cls.user_a.id])],
        })

    # ========================
    # Helpers (D2 multi-company tests)
    # ========================

    _user_seq = 0
    _cash_seq = 0
    _safe_seq = 0

    def _make_user(self, groups):
        """Creates a treasury user restricted to the current (default)
        company only -- required to exercise the D2 company-blindness
        tests below."""
        self.__class__._user_seq += 1
        n = self._user_seq
        group = self.env.ref(groups)
        return self.env['res.users'].create({
            'name': f'ACL User {n}',
            'login': f'acl_user_{n}',
            'email': f'acl_user_{n}@example.com',
            'group_ids': [(6, 0, [group.id])],
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
        })

    def _make_cash(self, company=None, **vals):
        self.__class__._cash_seq += 1
        n = self._cash_seq
        company = company or self.env.company
        journal = self.env['account.journal'].create({
            'name': f'D2 Journal {n}', 'type': 'cash',
            'code': f'D2J{n}', 'company_id': company.id,
        })
        vals.setdefault('name', f'D2 Cash {n}')
        vals.setdefault('code', f'D2C{n}')
        vals.setdefault('journal_id', journal.id)
        vals.setdefault('company_id', company.id)
        return self.env['oski.treasury.cash'].create(vals)

    def _make_safe(self, company=None, **vals):
        self.__class__._safe_seq += 1
        n = self._safe_seq
        company = company or self.env.company
        vals.setdefault('name', f'D2 Safe {n}')
        vals.setdefault('code', f'D2S{n}')
        vals.setdefault('company_id', company.id)
        vals.setdefault(
            'responsible_ids', [(6, 0, [self.env.ref('base.user_admin').id])]
        )
        return self.env['oski.treasury.safe'].create(vals)

    # ========================
    # Ported from adi_treasury.test_treasury_access (source v15/v18)
    # ========================

    def test_01_authorized_user_sees_cash(self):
        found = self.env['oski.treasury.cash'].with_user(self.user_a).search(
            [('id', '=', self.cash_a.id)])
        self.assertEqual(found, self.cash_a)

    def test_02_unauthorized_user_cannot_see_cash(self):
        found = self.env['oski.treasury.cash'].with_user(self.user_b).search(
            [('id', '=', self.cash_a.id)])
        self.assertFalse(found, "B must not see A's cash register")
        with self.assertRaises(AccessError):
            self.env['oski.treasury.cash'].with_user(self.user_b).browse(
                self.cash_a.id).read(['current_balance'])

    def test_03_safe_viewer_access(self):
        """The safe is viewable by a user listed in user_ids."""
        found = self.env['oski.treasury.safe'].with_user(self.user_a).search(
            [('id', '=', self.safe_a.id)])
        self.assertEqual(found, self.safe_a)
        found_b = self.env['oski.treasury.safe'].with_user(self.user_b).search(
            [('id', '=', self.safe_a.id)])
        self.assertFalse(found_b, "B (not authorized) must not see the safe")

    # ========================
    # D2 - company-scoped record rules
    # ========================

    def test_d2_manager_other_company_blind(self):
        """A manager, even with full visibility on his own company, is
        blind to a cash register belonging to another company (no more
        [(1, '=', 1)])."""
        company2 = self.env['res.company'].create({'name': 'ACL Company 2'})
        cash2 = self._make_cash(company=company2)
        mgr = self._make_user('oski_treasury.group_treasury_manager')  # company 1 only
        self.assertNotIn(
            cash2.id,
            self.env['oski.treasury.cash'].with_user(mgr).search([]).ids,
        )

    def test_d2_user_own_company_only(self):
        """A user assigned via user_ids on a cash register of ANOTHER
        company still cannot see it: the company scope is AND-ed with the
        assignment domain, not OR-ed."""
        company2 = self.env['res.company'].create({'name': 'ACL Company 3'})
        user = self._make_user('oski_treasury.group_treasury_user')  # company 1 only
        cash2 = self._make_cash(company=company2, user_ids=[(6, 0, [user.id])])
        self.assertNotIn(
            cash2.id,
            self.env['oski.treasury.cash'].with_user(user).search([]).ids,
        )

    def test_d2_operation_follows_cash_company(self):
        """A cash operation's company_id follows its cash register
        (related, stored): a manager blind to the cash register is also
        blind to its operations."""
        company2 = self.env['res.company'].create({'name': 'ACL Company 4'})
        cash2 = self._make_cash(company=company2)
        category = self.env.ref('oski_treasury.category_vente')
        op2 = self.env['oski.treasury.cash.operation'].create({
            'cash_id': cash2.id, 'operation_type': 'in',
            'category_id': category.id, 'amount': 100.0,
        })
        mgr = self._make_user('oski_treasury.group_treasury_manager')  # company 1 only
        self.assertNotIn(
            op2.id,
            self.env['oski.treasury.cash.operation'].with_user(mgr).search([]).ids,
        )

    def test_d2_transfer_legs_same_company(self):
        """A transfer's legs (cash/safe) must all belong to the transfer's
        own company: referencing a foreign-company cash register/safe as a
        leg must be rejected, while a normal same-company transfer must
        still go through."""
        company2 = self.env['res.company'].create({'name': 'ACL Company 5'})
        cash_own = self._make_cash()
        cash_foreign = self._make_cash(company=company2)

        with self.assertRaises(ValidationError):
            self.env['oski.treasury.transfer'].create({
                'transfer_type': 'cash_to_cash',
                'cash_from_id': cash_own.id,
                'cash_to_id': cash_foreign.id,
                'amount': 100.0,
                'company_id': self.env.company.id,
            })

        # Same-company transfer must not be blocked.
        cash_own_2 = self._make_cash()
        transfer = self.env['oski.treasury.transfer'].create({
            'transfer_type': 'cash_to_cash',
            'cash_from_id': cash_own.id,
            'cash_to_id': cash_own_2.id,
            'amount': 100.0,
            'company_id': self.env.company.id,
        })
        self.assertTrue(transfer.id)

    # ========================
    # ORM lock: safe responsibles reserved to Safe Administrators
    # ========================

    def test_safe_admin_lock(self):
        """safe_admin implies manager, not the reverse: a plain manager
        (without the safe_admin group) is denied by the ORM lock even
        though the record rule and ACL would otherwise let the write
        through."""
        mgr = self._make_user('oski_treasury.group_treasury_manager')
        with self.assertRaises(AccessError):
            self.safe_a.with_user(mgr).write({'responsible_ids': [(4, mgr.id)]})

    # ========================
    # Odoo 20 (ir.access): permissions OR-ed per group, company scope as a
    # group-less restriction AND-ed for everyone.
    # ========================

    def test_v20_internal_user_without_treasury_group_denied(self):
        """A plain internal user (no treasury group) gets no permission at
        all on the treasury models: search is refused, not just empty."""
        internal = self.env['res.users'].create({
            'name': 'Plain Internal', 'login': 'plain_internal_acl',
            'email': 'plain_internal_acl@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        for model in ('oski.treasury.cash', 'oski.treasury.cash.operation',
                      'oski.treasury.cash.closing', 'oski.treasury.safe',
                      'oski.treasury.safe.operation', 'oski.treasury.transfer',
                      'oski.treasury.operation.category'):
            Model = self.env[model].with_user(internal)
            self.assertFalse(Model.has_access('read'), model)
            with self.assertRaises(AccessError, msg=model):
                Model.search([])
        with self.assertRaises(AccessError):
            self.cash_a.with_user(internal).read(['name'])

    def test_v20_manager_sees_only_allowed_companies(self):
        """A manager of two companies sees both registers only when both
        companies are allowed in the context; restricting
        allowed_company_ids hides the other one (restriction AND-ed with
        the manager's unrestricted permission)."""
        company2 = self.env['res.company'].create({'name': 'ACL Company 6'})
        cash2 = self._make_cash(company=company2)
        cash1 = self._make_cash()
        mgr = self._make_user('oski_treasury.group_treasury_manager')
        mgr.write({'company_ids': [(4, company2.id)]})
        Cash = self.env['oski.treasury.cash'].with_user(mgr)
        both = Cash.with_context(
            allowed_company_ids=[self.env.company.id, company2.id]).search([])
        self.assertIn(cash1, both)
        self.assertIn(cash2, both)
        only1 = Cash.with_context(allowed_company_ids=[self.env.company.id]).search([])
        self.assertIn(cash1, only1)
        self.assertNotIn(cash2, only1)

    def test_v20_user_write_limited_to_assigned_cash(self):
        """The user permission ('ru' + assignment domain) does not grant
        write on a register the user is not assigned to, nor create."""
        with self.assertRaises(AccessError):
            self.cash_a.with_user(self.user_b).write({'location': 'X'})
        self.cash_a.with_user(self.user_a).write({'location': 'Desk'})
        self.assertEqual(self.cash_a.location, 'Desk')
        with self.assertRaises(AccessError):
            self.env['oski.treasury.cash'].with_user(self.user_a).create({
                'name': 'Nope', 'code': 'NOPE',
                'journal_id': self.journal_cash.id,
            })
