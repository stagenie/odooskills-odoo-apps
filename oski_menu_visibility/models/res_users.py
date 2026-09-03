from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    oski_hidden_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "oski_user_hidden_menu_rel", "user_id", "menu_id",
        string="Menus masqués",
        help="Menus retirés de l'écran de cet utilisateur. Masquer un menu masque "
             "aussi tout ce qu'il contient.",
    )

    def _oski_invalidate_menu_cache(self):
        # ``ir.ui.menu.load_menus`` est mis en cache par utilisateur : tant
        # qu'il n'est pas vidé, l'écran garde les menus d'avant.
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any("oski_hidden_menu_ids" in vals for vals in vals_list):
            users._oski_invalidate_menu_cache()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "oski_hidden_menu_ids" in vals:
            self._oski_invalidate_menu_cache()
        return res
