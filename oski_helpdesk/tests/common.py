from odoo.tests.common import TransactionCase


class HelpdeskCase(TransactionCase):

    def _make_user(self, login, groups=None):
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "groups_id": [(6, 0, [g.id for g in (groups or [])])],
        })
