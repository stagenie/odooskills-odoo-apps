from odoo.exceptions import AccessError
from odoo.tests import new_test_user

from .common import RentalCase


class TestRentalSecurity(RentalCase):
    """Droits (ir.access) : groupes Location et cloisonnement multi-société."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Société B location'})
        cls.asset_a = cls._make_asset('Ressource A')
        cls.asset_b = cls._make_asset('Ressource B', company_id=cls.company_b.id)
        cls.rental_user = new_test_user(
            cls.env, login='rental_user_a', groups='oski_rental.group_rental_user',
            company_id=cls.env.company.id, company_ids=[cls.env.company.id])
        cls.internal = new_test_user(
            cls.env, login='rental_no_group', groups='base.group_user')

    def test_other_company_hidden(self):
        Asset = self.env['oski.rental.asset'].with_user(self.rental_user)
        found = Asset.search([('id', 'in', (self.asset_a | self.asset_b).ids)])
        self.assertEqual(found, self.asset_a)
        with self.assertRaises(AccessError):
            self.asset_b.with_user(self.rental_user).read(['name'])

    def test_user_cannot_delete_asset(self):
        with self.assertRaises(AccessError):
            self.asset_a.with_user(self.rental_user).unlink()

    def test_category_read_only_for_user(self):
        with self.assertRaises(AccessError):
            self.env['oski.rental.category'].with_user(self.rental_user).create(
                {'name': 'Interdit'})

    def test_internal_without_group_denied(self):
        with self.assertRaises(AccessError):
            self.env['oski.rental.order'].with_user(self.internal).search([])
