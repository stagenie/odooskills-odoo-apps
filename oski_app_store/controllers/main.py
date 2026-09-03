"""Contrôleur HTTP du store de modules OdooSkills.

Route Task 9 : /apps/download/<version_id>
  - module non publié → 404
  - module gratuit → servi à tous (public inclus)
  - module payant, public → redirect vers /web/login
  - module payant, connecté sans achat confirmé → redirect vers la page module
  - module payant, acheteur confirmé (sale.order.line state='sale') → zip servi
"""
import time
from urllib.parse import urlencode, urlparse

from odoo import _, http
from odoo.http import request
from odoo.addons.oski_app_store.controllers.url_state import build_query, toggle

# Un visiteur qui rafraîchit la page ou relance le téléchargement ne doit pas
# gonfler le compteur public à chaque clic : une seule incrémentation par
# version et par session dans cette fenêtre.
DOWNLOAD_COUNT_GUARD_SECONDS = 6 * 3600


class OskiAppStore(http.Controller):
    """Contrôleur principal du store OdooSkills App Store."""

    def _version_state(self):
        """(supported, default, upcoming) depuis le référentiel oski.odoo.version.

        `supported` est trié de la plus récente à la plus ancienne — l'ordre
        d'affichage partout dans le site. `upcoming` liste les versions
        annoncées sans archive (Odoo 20 avant sa sortie).
        """
        Versions = request.env["oski.odoo.version"].sudo()
        supported = Versions.get_supported()
        if not supported:
            return ["19.0"], "19.0", []  # garde-fou base vide
        return supported, Versions.get_default(), Versions.get_upcoming()

    @http.route(["/apps"], type="http", auth="public", website=True, sitemap=True)
    def apps_catalog(self, **kw):
        """Catalogue public avec facettes (catégorie/tags/prix), tri et version.

        Behavior B : aucun module masqué par la version (pills + tri compatibles-d'abord).
        Filtrage : OR intra-groupe (ORM `in`), AND inter-groupes (conjonction).
        État partageable + encodé via url_state.build_query.
        """
        supported_versions, default_version, upcoming_versions = self._version_state()
        released_versions = [
            pv for pv in supported_versions if pv not in upcoming_versions
        ]

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
        search = args.get("search", "").strip()[:120]
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

        show_counters, _min = request.env["oski.module"]._counters_settings()

        modules = request.env["oski.module"].search(domain)
        if sort == "recent":
            modules = modules.sorted(
                key=lambda m: (not m.supports(version), -m.create_date.timestamp())
            )
        elif sort == "downloads" and show_counters:
            modules = modules.sorted(
                key=lambda m: (not m.supports(version), -m.download_count)
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
            for key, label in (("all", _("All")), ("free", _("Free")), ("premium", _("Premium")))
        ]
        sort_choices = [("name", _("Name")), ("recent", _("Recent"))]
        if show_counters:
            sort_choices.append(("downloads", _("Most downloaded")))
        sort_options = [
            {
                "key": key,
                "label": label,
                "selected": sort == key,
                "href": build_query(cats, tags, pricing, key, search, version, default_version),
            }
            for key, label in sort_choices
        ]
        # Plus récente d'abord, versions à venir en tête : le visiteur cherche
        # d'abord la version qu'il installe aujourd'hui ou demain.
        def _version_option(pv):
            return {
                "label": pv,
                "selected": pv == version,
                "soon": pv in upcoming_versions,
                # QWeb n'expose pas `_` dans son contexte de rendu : le titre
                # traduit (annonce "pas encore sortie") se construit ici, pas
                # dans une expression t-att-title du gabarit.
                "title": _("Odoo %s — not released yet") % pv if pv in upcoming_versions else pv,
                "note": _("soon") if pv in upcoming_versions else "",
                "href": build_query(cats, tags, pricing, sort, search, pv, default_version),
            }

        version_pills = [_version_option(pv) for pv in supported_versions]
        version_spectrum = [_version_option(pv) for pv in supported_versions]
        OskiModule = request.env["oski.module"].sudo()

        meta_description = _(
            "Ready-to-install Odoo modules, free and premium, by OdooSkills — "
            "compatible from %s to %s."
        ) % (released_versions[-1], released_versions[0])
        if upcoming_versions:
            meta_description += _(" Odoo %s is at the door.") % (
                upcoming_versions[0].split(".")[0]
            )

        values = {
            "modules": modules,
            "version_spectrum": version_spectrum,
            "catalog_count": OskiModule.search_count([]),
            "free_count": OskiModule.search_count([("is_free", "=", True)]),
            "category_options": category_options,
            "tag_options": tag_options,
            "pricing_options": pricing_options,
            "sort_options": sort_options,
            "version_pills": version_pills,
            # Pastilles de compatibilité des cartes : uniquement les versions
            # sorties (une pastille toujours éteinte sur chaque carte n'apprend
            # rien au visiteur).
            "card_versions": released_versions,
            "released_versions": released_versions,
            "upcoming_versions": upcoming_versions,
            "version": version,
            "version_is_upcoming": version in upcoming_versions,
            "search": search,
            "sort": sort,
            "show_counters": show_counters,
            "has_filters": bool(cats or tags or pricing != "all" or search),
            "clear_url": "/apps",
            # Une seule phrase traduisible : mélanger un msgid tronqué avec un
            # nœud texte statique produirait un français aux guillemets
            # incohérents (cf. _version_option, même stratégie).
            "empty_title": _("No module for “%s”.") % search if search
            else _("No module matches these filters."),
            # Pré-remplissage du formulaire de demande de module depuis l'état
            # « aucun résultat » : on reprend la recherche et la première
            # catégorie active, sans le "?" (le gabarit l'ajoute lui-même).
            "prefill_query": urlencode(
                {k: v for k, v in (("subject", search[:120]), ("category", cats[0] if cats else "")) if v}
            ),
            # Référencement : sans ces deux clés, chaque page hérite du titre
            # générique du site et n'a aucune description.
            "additional_title": _("Odoo modules"),
            "website_meta_description": meta_description,
        }
        return request.render("oski_app_store.catalog_page", values)

    def _catalog_back_url(self):
        """URL de retour vers le catalogue, filtres conservés.

        N'accepte que les Referer du même host pointant exactement sur /apps
        (anti open-redirect) ; sinon fallback /apps nu.
        """
        referer = request.httprequest.headers.get("Referer", "")
        parsed = urlparse(referer)
        if parsed.path == "/apps" and (
            not parsed.netloc or parsed.netloc == request.httprequest.host
        ):
            return "/apps?%s" % parsed.query if parsed.query else "/apps"
        return "/apps"

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
        supported_versions, default_version, upcoming_versions = self._version_state()
        version = v if v in supported_versions else default_version
        partner = (
            request.env.user.partner_id
            if not request.env.user._is_public()
            else False
        )
        # Le produit est lu en sudo : un visiteur public n'a pas accès à
        # product.template, et la fiche rendait 403 dès qu'un module payant
        # était publié. Le bouton d'achat n'apparaît que si le produit est
        # lui-même publié — sinon la mise au panier refuserait le produit.
        product = module.sudo().product_tmpl_id
        variant = product.product_variant_id
        is_sellable = bool(variant) and product.is_published and product.sale_ok
        # Même raison que _version_option côté catalogue : le titre traduit
        # ("pas encore sortie") ne peut pas se construire dans le gabarit,
        # QWeb n'y expose pas `_`.
        pill_versions = [
            {
                "version": pv,
                "title": _("Odoo %s — not released yet") % pv if pv in upcoming_versions else pv,
            }
            for pv in supported_versions
        ]
        return request.render(
            "oski_app_store.module_page",
            {
                "module": module,
                "version": version,
                "show_counters": request.env["oski.module"]._counters_settings()[0],
                "is_purchased": module.is_purchased_by(partner),
                "is_sellable": is_sellable,
                "buy_url": "/apps/buy/%s" % module.id if variant else "",
                "pill_versions": pill_versions,
                "upcoming_versions": upcoming_versions,
                # main_object : le titre de l'onglet, l'aperçu de partage et le
                # panneau de référencement de l'éditeur s'y accrochent.
                "main_object": module,
                "additional_title": module.name,
                "website_meta_description": module._seo_description(),
                "screenshots": module.sudo().screenshot_ids.sorted("name"),
                "back_url": self._catalog_back_url(),
            },
        )

    @http.route(
        ["/apps/buy/<int:module_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def apps_buy(self, module_id, **kw):
        """Met le module au panier puis renvoie sur `/shop/cart`.

        En Odoo 19, `/shop/cart/update` est une route **jsonrpc en POST** : le
        lien GET que portait la fiche n'ajoutait rien et le visiteur voyait un
        panier vide, sans erreur. Le store a besoin d'un lien franc, d'où cette
        route maison qui applique la même règle de vente que la fiche.
        """
        module = request.env["oski.module"].sudo().browse(module_id).exists()
        if not module or not module.is_published:
            return request.not_found()

        product = module.product_tmpl_id
        variant = product.product_variant_id
        if not variant or not product.is_published or not product.sale_ok:
            return request.redirect(module.website_url)

        order_sudo = request.cart or request.website._create_cart()
        # Un module est un fichier : le racheter n'a pas de sens. Un
        # rafraîchissement de la page ne doit donc jamais doubler la quantité.
        already = order_sudo.order_line.filtered(
            lambda sol: sol.product_id == variant
        )
        if not already:
            order_sudo.with_context(skip_cart_verification=True)._cart_add(
                product_id=variant.id, quantity=1
            )

        return request.redirect("/shop/cart")

    def _should_count_download(self, version_id):
        """True une fois par session et par version, dans une fenêtre de 6 h.

        Le compteur reste dans `request.session` (JSON-sérialisable : clés
        str, valeurs float) et purge au passage les entrées expirées pour ne
        pas laisser grossir la session indéfiniment.
        """
        key = str(version_id)
        now = time.time()
        counted = dict(request.session.get("oski_dl_counted") or {})
        counted = {
            k: ts for k, ts in counted.items()
            if now - ts < DOWNLOAD_COUNT_GUARD_SECONDS
        }
        last = counted.get(key)
        should_count = last is None
        counted[key] = now
        request.session["oski_dl_counted"] = counted
        return should_count

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

            # Utilisateur connecté : vérifier une commande confirmée.
            # Une seule règle d'entitlement, partagée avec la fiche publique.
            if not module.is_purchased_by(request.env.user.partner_id):
                return request.redirect(module.website_url)

        if self._should_count_download(version.id):
            version._bump_download_count()

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
