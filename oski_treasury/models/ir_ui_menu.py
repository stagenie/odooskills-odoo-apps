# -*- coding: utf-8 -*-
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        user = self.env.user
        if user.has_group('oski_treasury.group_treasury_manager'):
            return visible
        # menu_treasury_cash / menu_treasury_safe: "Operations" sub-menus
        # leading to the cash register / safe lists. menu_treasury_cash_shortcut
        # and menu_treasury_safe_shortcut (root-level kanban shortcuts) point to
        # the same actions and are hidden the same way.
        to_check = {
            'oski_treasury.menu_treasury_cash': 'has_treasury_cash',
            'oski_treasury.menu_treasury_cash_shortcut': 'has_treasury_cash',
            'oski_treasury.menu_treasury_safe': 'has_treasury_safe',
            'oski_treasury.menu_treasury_safe_shortcut': 'has_treasury_safe',
        }
        for xmlid, flag in to_check.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.id in visible and not user[flag]:
                visible -= {menu.id}
        return visible
