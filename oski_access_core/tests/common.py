# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class OskiAccessCase(TransactionCase):

    def _make_user(self, login, groups=None):
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "group_ids": [(6, 0, [g.id for g in (groups or [])])],
        })
