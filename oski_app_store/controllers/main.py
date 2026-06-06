"""Contrôleur HTTP du store de modules OdooSkills.

Route Task 9 : /apps/download/<version_id>
  - module non publié → 404
  - module gratuit → servi à tous (public inclus)
  - module payant, public → redirect vers /web/login
  - module payant, connecté sans achat confirmé → redirect vers la page module
  - module payant, acheteur confirmé (sale.order.line state='sale') → zip servi
"""
from odoo import http
from odoo.http import request


class OskiAppStore(http.Controller):
    """Contrôleur principal du store OdooSkills App Store."""

    # Versions Odoo supportées par le store (source : oski.module.version).
    SUPPORTED_VERSIONS = ["19.0", "18.0", "17.0", "16.0", "15.0"]
    DEFAULT_VERSION = "19.0"

    @http.route(["/apps"], type="http", auth="public", website=True, sitemap=True)
    def apps_catalog(self, category=None, search=None, v=None, **kw):
        """Catalogue public des modules publiés (filtre catégorie + recherche + version).

        `v` = version Odoo cible (15.0..19.0). Filtre les modules ayant une
        version pour `v` et adapte le sous-titre. Défaut : DEFAULT_VERSION.
        """
        version = v if v in self.SUPPORTED_VERSIONS else self.DEFAULT_VERSION
        Module = request.env["oski.module"]
        domain = [
            ("is_published", "=", True),
            ("version_line_ids.odoo_version", "=", version),
        ]
        if category:
            domain.append(("category_id", "=", int(category)))
        if search:
            domain.append(("name", "ilike", search))
        modules = Module.search(domain)
        categories = request.env["oski.module.category"].search([])
        values = {
            "modules": modules,
            "categories": categories,
            "search": search or "",
            "active_category": int(category) if category else False,
            "version": version,
            "versions": self.SUPPORTED_VERSIONS,
        }
        return request.render("oski_app_store.catalog_page", values)

    @http.route(
        ['/apps/<model("oski.module"):module>'],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def apps_module_page(self, module, **kw):
        """Page détail d'un module. Non publié → 404 sauf gestionnaire."""
        if not module.is_published and not request.env.user.has_group(
            "oski_app_store.group_manager"
        ):
            return request.not_found()
        return request.render("oski_app_store.module_page", {"module": module})

    @http.route(
        ["/apps/download/<int:version_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def apps_download(self, version_id, **kw):
        """Sert l'archive .zip d'un module avec vérification d'entitlement.

        Logique :
        1. Version inexistante ou sans pièce jointe → 404
        2. Module non publié → 404
        3. Module gratuit → téléchargement direct sans authentification
        4. Module payant, visiteur public → redirect /web/login
        5. Module payant, utilisateur connecté sans commande confirmée → redirect page module
        6. Module payant, acheteur confirmé → téléchargement
        """
        # Lecture sudo pour contourner les record rules publiques (version non visible
        # au public si le module est non publié — on gère l'accès manuellement ci-dessous).
        version = request.env["oski.module.version"].sudo().browse(version_id)

        if not version.exists() or not version.attachment_id:
            return request.not_found()

        module = version.module_id

        # Refus explicite pour les modules non publiés
        if not module.is_published:
            return request.not_found()

        # Entitlement pour modules payants
        if not module.is_free:
            if request.env.user._is_public():
                # Visiteur anonyme : redirection vers la page de connexion
                return request.redirect(
                    "/web/login?redirect=%s" % module.website_url
                )

            # Utilisateur connecté : vérifier une commande confirmée
            partner = request.env.user.partner_id
            entitled = (
                request.env["sale.order.line"]
                .sudo()
                .search_count(
                    [
                        ("order_partner_id", "=", partner.id),
                        (
                            "product_id.product_tmpl_id",
                            "=",
                            module.product_tmpl_id.id,
                        ),
                        ("state", "=", "sale"),
                    ]
                )
            )
            if not entitled:
                return request.redirect(module.website_url)

        # Lecture sudo de la pièce jointe pour garantir l'accès au binaire
        attachment = version.attachment_id.sudo()
        filename = "%s-%s.zip" % (module.technical_name, version.module_version)
        data = attachment.raw

        return request.make_response(
            data,
            headers=[
                ("Content-Type", "application/zip"),
                ("Content-Disposition", http.content_disposition(filename)),
                ("Content-Length", len(data)),
            ],
        )
