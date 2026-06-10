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
from odoo.addons.oski_app_store.controllers.url_state import build_query, toggle


class OskiAppStore(http.Controller):
    """Contrôleur principal du store OdooSkills App Store."""

    def _version_state(self):
        """(supported, default) depuis le référentiel oski.odoo.version."""
        Versions = request.env["oski.odoo.version"].sudo()
        supported = Versions.get_supported()
        if not supported:
            return ["19.0"], "19.0"  # garde-fou base vide
        return supported, Versions.get_default()

    @http.route(["/apps"], type="http", auth="public", website=True, sitemap=True)
    def apps_catalog(self, **kw):
        """Catalogue public avec facettes (catégorie/tags/prix), tri et version.

        Behavior B : aucun module masqué par la version (pills + tri compatibles-d'abord).
        Filtrage : OR intra-groupe (ORM `in`), AND inter-groupes (conjonction).
        État partageable + encodé via url_state.build_query.
        """
        supported_versions, default_version = self._version_state()

        args = request.httprequest.args

        def _ints(key):
            out = []
            for raw in args.getlist(key):
                try:
                    out.append(int(raw))
                except (TypeError, ValueError):
                    continue
            return out

        cats = _ints("category")
        tags = _ints("tag")
        pricing = args.get("pricing", "all")
        sort = args.get("sort", "name")
        search = args.get("search", "")
        v = args.get("v")
        version = v if v in supported_versions else default_version

        domain = [("is_published", "=", True)]
        if cats:
            domain.append(("category_id", "in", cats))
        if tags:
            domain.append(("tag_ids", "in", tags))
        if pricing == "free":
            domain.append(("is_free", "=", True))
        elif pricing == "premium":
            domain.append(("is_free", "=", False))
        if search:
            domain.append(("name", "ilike", search))

        modules = request.env["oski.module"].search(domain)
        if sort == "recent":
            modules = modules.sorted(
                key=lambda m: (not m.supports(version), -m.create_date.timestamp())
            )
        else:
            modules = modules.sorted(
                key=lambda m: (not m.supports(version), m.name.lower())
            )

        categories = request.env["oski.module.category"].search([])
        all_tags = request.env["oski.module.tag"].search([])

        category_options = [
            {
                "id": c.id,
                "name": c.name,
                "selected": c.id in cats,
                "href": build_query(toggle(cats, c.id), tags, pricing, sort, search, version, default_version),
            }
            for c in categories
        ]
        tag_options = [
            {
                "id": t.id,
                "name": t.name,
                "color": t.color,
                "selected": t.id in tags,
                "href": build_query(cats, toggle(tags, t.id), pricing, sort, search, version, default_version),
            }
            for t in all_tags
        ]
        pricing_options = [
            {
                "key": key,
                "label": label,
                "selected": pricing == key,
                "href": build_query(cats, tags, key, sort, search, version, default_version),
            }
            for key, label in (("all", "Tous"), ("free", "Gratuit"), ("premium", "Premium"))
        ]
        sort_options = [
            {
                "key": key,
                "label": label,
                "selected": sort == key,
                "href": build_query(cats, tags, pricing, key, search, version, default_version),
            }
            for key, label in (("name", "Nom"), ("recent", "Récents"))
        ]
        version_pills = [
            {
                "label": pv,
                "selected": pv == version,
                "href": build_query(cats, tags, pricing, sort, search, pv, default_version),
            }
            for pv in reversed(supported_versions)
        ]

        values = {
            "modules": modules,
            "category_options": category_options,
            "tag_options": tag_options,
            "pricing_options": pricing_options,
            "sort_options": sort_options,
            "version_pills": version_pills,
            "version": version,
            "search": search,
            "sort": sort,
            "has_filters": bool(cats or tags or pricing != "all" or search),
            "clear_url": "/apps",
        }
        return request.render("oski_app_store.catalog_page", values)

    @http.route(
        ['/apps/<model("oski.module"):module>'],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def apps_module_page(self, module, v=None, **kw):
        """Page détail d'un module. Non publié → 404 sauf gestionnaire."""
        if not module.is_published and not request.env.user.has_group(
            "oski_app_store.group_manager"
        ):
            return request.not_found()
        supported_versions, default_version = self._version_state()
        version = v if v in supported_versions else default_version
        return request.render(
            "oski_app_store.module_page",
            {
                "module": module,
                "version": version,
                "pill_versions": list(reversed(supported_versions)),
                "screenshots": module.sudo().screenshot_ids.sorted("name"),
            },
        )

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
