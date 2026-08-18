from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _filter_visible_menus(self):
        """Retire de l'écran les menus masqués pour l'utilisateur courant.

        Le filtrage se greffe ici et non sur ``_visible_menu_ids`` : cette
        dernière est mise en cache sur l'ensemble des **groupes** de
        l'utilisateur, si bien qu'un masquage individuel y serait servi à tous
        ceux qui partagent ses groupes. ``_filter_visible_menus`` n'est pas
        mise en cache, et son appelant ``load_menus`` l'est par utilisateur :
        c'est le seul point où un réglage personnel reste personnel.
        """
        menus = super()._filter_visible_menus()
        hidden = self.env.user.sudo().oski_hidden_menu_ids
        if not hidden:
            return menus
        hidden_ids = set(hidden.ids)
        # ``parent_path`` porte le chemin complet ("1/5/9/") : un menu masqué
        # emporte donc ses descendants sans requête supplémentaire.
        prefixes = tuple(path for path in hidden.mapped("parent_path") if path)
        return menus.filtered(
            lambda menu: menu.id not in hidden_ids
            and not (prefixes and menu.parent_path and menu.parent_path.startswith(prefixes))
        )
