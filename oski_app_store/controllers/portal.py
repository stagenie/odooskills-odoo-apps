"""Espace client du store : « Mes applications ».

Après paiement, l'acheteur doit retrouver ses modules et pouvoir les
retélécharger — toutes versions Odoo confondues. Sans cette page, la fiche
publique restait le seul point d'entrée et n'y menait pas.
"""
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class OskiAppStorePortal(CustomerPortal):
    """Ajoute /my/apps et son compteur à l'espace client."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "app_count" in counters:
            values["app_count"] = len(
                request.env["oski.module"].purchased_by(request.env.user.partner_id)
            )
        return values

    @http.route(["/my/apps"], type="http", auth="user", website=True)
    def portal_my_apps(self, **kw):
        """Liste les modules achetés par le partenaire connecté."""
        modules = request.env["oski.module"].purchased_by(
            request.env.user.partner_id
        )
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "modules": modules.sorted("name"),
                "page_name": "apps",
                "default_url": "/my/apps",
            }
        )
        return request.render("oski_app_store.portal_my_apps", values)
