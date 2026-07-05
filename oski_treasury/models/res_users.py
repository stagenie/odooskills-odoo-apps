# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_treasury_cash = fields.Boolean(compute='_compute_treasury_access')
    has_treasury_safe = fields.Boolean(compute='_compute_treasury_access')

    def _compute_treasury_access(self):
        for user in self:
            if user.has_group('oski_treasury.group_treasury_manager'):
                user.has_treasury_cash = user.has_treasury_safe = True
                continue
            # Users outside the treasury groups have no ACL on our models:
            # searching as them would raise AccessError. No access, no menu.
            if not user.has_group('oski_treasury.group_treasury_user'):
                user.has_treasury_cash = user.has_treasury_safe = False
                continue
            env = self.env(user=user.id)
            user.has_treasury_cash = bool(env['oski.treasury.cash'].search_count([], limit=1))
            user.has_treasury_safe = bool(env['oski.treasury.safe'].search_count([], limit=1))
