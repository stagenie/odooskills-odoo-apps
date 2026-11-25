"""Contrôleur HTTP du store de modules OdooSkills.

Route Task 9 : /apps/download/<version_id>
  - module non publié → 404
  - module gratuit → servi à tous (public inclus)
  - module payant, public → redirect vers /web/login
  - module payant, connecté sans achat confirmé → redirect vers la page module
  - module payant, acheteur confirmé (sale.order.line state='sale') → zip servi
"""
import logging
import re
import time
from urllib.parse import urlencode, urlparse

from babel.dates import format_date as babel_format_date

from odoo import _, http
from odoo.http import request
from odoo.tools.misc import babel_locale_parse, formatLang
from odoo.addons.oski_app_store.controllers.url_state import build_query, query_params, toggle

# Un visiteur qui rafraîchit la page ou relance le téléchargement ne doit pas
# gonfler le compteur public à chaque clic : une seule incrémentation par
# version et par session dans cette fenêtre.
DOWNLOAD_COUNT_GUARD_SECONDS = 6 * 3600

# Cartes par page du catalogue : la grille passe de 1 à 2, 3 puis 4 colonnes
# (row-cols-1 / sm-2 / md-3 / xl-4). 24 est le plus petit multiple commun
# de 2, 3 et 4 au-delà de 12 : chaque page pleine remplit toutes ses rangées,
# quel que soit l'écran (6 rangées de 4, 8 de 3, 12 de 2).
CATALOG_PAGE_SIZE = 24
# Suites montrées dans le bandeau du catalogue (les autres : filtre « Suites »).
SUITE_BAND_SIZE = 8

_logger = logging.getLogger(__name__)


class OskiAppStore(http.Controller):
    """Contrôleur principal du store OdooSkills App Store."""

    def _version_state(self):
        """(supported, default, upcoming) depuis le référentiel oski.odoo.version.

        `supported` est trié de la plus récente à la plus ancienne — l'ordre
        d'affichage partout dans le site. `upcoming` liste les versions
        sans archive : Odoo 20 est sorti, ses archives arrivent module par module.
        """
        Versions = request.env["oski.odoo.version"].sudo()
        supported = Versions.get_supported()
        if not supported:
            return ["19.0"], "19.0", []  # garde-fou base vide
        return supported, Versions.get_default(), Versions.get_upcoming()

    @http.route(["/apps", "/apps/page/<int:page>"], type="http", auth="public",
                website=True, sitemap=True)
    def apps_catalog(self, page=1, **kw):
        """Catalogue public avec facettes (catégorie/prix), tri et version.

        Behavior B : aucun module masqué par la version (pills + tri compatibles-d'abord).
        Filtrage : OR intra-groupe (ORM `in`), AND inter-groupes (conjonction).
        État partageable + encodé via url_state.build_query.
        """
        supported_versions, default_version, upcoming_versions = self._version_state()
        released_versions = [
            pv for pv in supported_versions if pv not in upcoming_versions
        ]
        # Versions anciennes servies à la demande : elles restent filtrables
        # (leurs archives existent), mais la phrase de compatibilité ne les
        # promet plus d'office. Repli sur `released` si tout est à la demande.
        on_request_versions = [
            pv for pv in request.env["oski.odoo.version"].sudo().get_on_request()
            if pv in released_versions
        ]
        standard_versions = [
            pv for pv in released_versions if pv not in on_request_versions
        ] or released_versions

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
        # Les étiquettes ne filtrent plus le catalogue (19.0.7.7.6) : un ancien
        # lien `?tag=` est redirigé vers la même vue sans ce paramètre.
        tags = []
        pricing = args.get("pricing", "all")
        sort = args.get("sort", "name")
        search = args.get("search", "").strip()[:120]
        v = args.get("v")
        version = v if v in supported_versions else default_version

        domain = [("is_published", "=", True)]
        if cats:
            domain.append(("category_id", "in", cats))
        if pricing == "free":
            domain.append(("is_free", "=", True))
        elif pricing == "premium":
            domain.append(("is_free", "=", False))
        elif pricing == "suite":
            domain.append(("is_suite", "=", True))
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

        # Pagination : le tri (compatibles d'abord) se fait en Python, la page
        # est donc découpée après le tri, sur l'ensemble filtré.
        filter_args = query_params(cats, tags, pricing, sort, search, version, default_version)
        total = len(modules)
        page_count = max(1, -(-total // CATALOG_PAGE_SIZE))
        if "tag" in args:
            target = "/apps/page/%d" % page if page > 1 else "/apps"
            return request.redirect(request.env["ir.http"]._url_for(build_query(
                cats, tags, pricing, sort, search, version, default_version, path=target)), code=301)
        if page == 1 and request.httprequest.path.rstrip("/").endswith("/page/1"):
            # /apps/page/1 doublonne /apps : une seule URL pour la page 1.
            # _url_for garde le préfixe de langue (/fr/...).
            return request.redirect(request.env["ir.http"]._url_for(build_query(
                cats, tags, pricing, sort, search, version, default_version)), code=301)
        if page < 1 or page > page_count:
            # Hors bornes (lien périmé après un filtre ou un retrait) : dernière
            # page existante, en redirection temporaire (le total varie).
            last = page_count if page > page_count else 1
            target = "/apps/page/%d" % last if last > 1 else "/apps"
            return request.redirect(request.env["ir.http"]._url_for(build_query(
                cats, tags, pricing, sort, search, version, default_version, path=target)))
        pager = request.website.pager(
            url="/apps", total=total, page=page, step=CATALOG_PAGE_SIZE,
            scope=5, url_args=filter_args,
        )
        modules = modules[pager["offset"]:pager["offset"] + CATALOG_PAGE_SIZE]

        categories = request.env["oski.module.category"].search([])

        category_options = [
            {
                "id": c.id,
                "name": c.name,
                "selected": c.id in cats,
                "href": build_query(toggle(cats, c.id), tags, pricing, sort, search, version, default_version),
            }
            for c in categories
        ]
        pricing_options = [
            {
                "key": key,
                "label": label,
                "selected": pricing == key,
                "href": build_query(cats, tags, key, sort, search, version, default_version),
            }
            for key, label in (
                ("all", _("All prices")), ("free", _("Open source")),
                ("premium", _("Premium")), ("suite", _("Suites")),
            )
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
                "on_request": pv in on_request_versions,
                # QWeb n'expose pas `_` dans son contexte de rendu : le titre
                # traduit se construit ici, pas dans une expression
                # t-att-title du gabarit.
                "title": (
                    _("Odoo %s — archives on the way") % pv if pv in upcoming_versions
                    else _("Odoo %s — on request") % pv if pv in on_request_versions
                    else pv
                ),
                "note": (
                    _("archives on the way") if pv in upcoming_versions
                    else _("on request") if pv in on_request_versions
                    else ""
                ),
                "href": build_query(cats, tags, pricing, sort, search, pv, default_version),
            }

        version_spectrum = [_version_option(pv) for pv in supported_versions]
        OskiModule = request.env["oski.module"].sudo()

        # Pas de borne haute : elle vieillit à chaque sortie d'Odoo.
        oldest_standard = standard_versions[-1].split(".")[0]
        on_request_label = ", ".join(
            pv.split(".")[0] for pv in reversed(on_request_versions)
        )
        meta_description = _(
            "Ready-to-install Odoo modules, open source and premium, by OdooSkills — "
            "for Odoo %s and later."
        ) % oldest_standard
        if on_request_label:
            meta_description += _(" Odoo %s on request.") % on_request_label

        additional_title = _("Odoo modules")
        if page > 1:
            # Titres distincts par page : pas de doublon de <title> en SEO.
            additional_title = _("Odoo modules — page %(page)s of %(count)s") % {
                "page": page, "count": page_count,
            }

        has_filters = bool(cats or tags or pricing != "all" or search)
        # Bandeau « Suites » : en tête de la page 1 du catalogue non filtré
        # (une recherche ou un filtre dit déjà ce que le visiteur veut voir).
        # Ordre : « Suite order » du backend, puis les plus grandes familles
        # d'abord (une nouvelle série prend sa place sans réglage).
        all_suites = OskiModule.search(
            [("is_suite", "=", True), ("is_published", "=", True)],
        ).sorted(lambda s: (s.suite_sequence, -len(s._suite_members()), s.name.lower()))
        featured_suites = (
            self._suite_offers(all_suites[:SUITE_BAND_SIZE])
            if page == 1 and not has_filters else []
        )
        values = {
            "featured_suites": featured_suites,
            "suites_all_label": _("All %s suites →") % len(all_suites),
            "suites_url": build_query([], [], "suite", "name", "", version, default_version),
            "modules": modules,
            "pager": pager,
            "result_total": total,
            "result_count_label": (
                _("1 module") if total == 1 else _("%s modules") % total
            ),
            # La carte « demande de module » (oski_dev_request) ne s'affiche
            # qu'en fin de catalogue, pas au bas de chaque page.
            "catalog_more_pages": page < page_count,
            "rel_prev": pager["page_previous"]["url"] if page > 1 else False,
            "rel_next": pager["page_next"]["url"] if page < page_count else False,
            "version_spectrum": version_spectrum,
            "catalog_count": OskiModule.search_count([]),
            "free_count": OskiModule.search_count([("is_free", "=", True)]),
            "category_options": category_options,
            "pricing_options": pricing_options,
            "sort_options": sort_options,
            # Pastilles de compatibilité des cartes : uniquement les versions
            # sorties (une pastille toujours éteinte sur chaque carte n'apprend
            # rien au visiteur).
            "card_versions": released_versions,
            "released_versions": released_versions,
            "oldest_standard": oldest_standard,
            "on_request_label": on_request_label,
            "upcoming_versions": upcoming_versions,
            "version": version,
            "version_is_upcoming": version in upcoming_versions,
            "search": search,
            "sort": sort,
            "show_counters": show_counters,
            "has_filters": has_filters,
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
            "additional_title": additional_title,
            "website_meta_description": meta_description,
        }
        return request.render("oski_app_store.catalog_page", values)

    def _catalog_back_url(self):
        """URL de retour vers le catalogue, filtres conservés.

        N'accepte que les Referer du même host pointant sur /apps ou /apps/page/<n>
        (anti open-redirect) ; sinon fallback /apps nu.
        """
        referer = request.httprequest.headers.get("Referer", "")
        parsed = urlparse(referer)
        # La page du catalogue (/apps/page/<n>) fait partie de l'état à rendre.
        if re.fullmatch(r"/apps(/page/[0-9]{1,4})?", parsed.path) and (
            not parsed.netloc or parsed.netloc == request.httprequest.host
        ):
            return "%s?%s" % (parsed.path, parsed.query) if parsed.query else parsed.path
        return "/apps"

    @http.route(
        ["/apps/m/<string:technical_name>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def apps_module_by_name(self, technical_name, **kw):
        """Lien stable vers la fiche d'un module, par son nom technique.

        L'URL canonique porte l'id de la base (`/apps/oski-school-fee-173`) :
        une fiche qui cite un autre module (la liste « What the suite
        installs » d'une suite) ne peut pas l'écrire dans son index.html.
        Elle pointe ici ; la route renvoie en 301 sur l'URL canonique, dans
        la langue de la requête. Module inconnu ou non publié → 404.
        """
        module = request.env["oski.module"].sudo().search(
            [("technical_name", "=", technical_name)], limit=1
        )
        if not module or not (
            module.is_published
            or request.env.user.has_group("oski_app_store.group_manager")
        ):
            return request.not_found()
        # request.redirect ne pose pas le préfixe de langue : /fr/apps/m/x
        # doit mener à /fr/apps/<slug>, pas à la page anglaise.
        return request.redirect(
            request.env["ir.http"]._url_for(module.website_url), code=301
        )

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
        price_offer = self._price_offer(product) if is_sellable else None
        # Même raison que _version_option côté catalogue : le titre traduit
        # ne peut pas se construire dans le gabarit, QWeb n'y expose pas `_`.
        on_request_versions = request.env["oski.odoo.version"].sudo().get_on_request()
        pill_versions = [
            {
                "version": pv,
                "title": (
                    _("Odoo %s — archives on the way") % pv if pv in upcoming_versions
                    else _("Odoo %s — on request") % pv if pv in on_request_versions
                    else pv
                ),
            }
            for pv in supported_versions
        ]
        # Essai 1 h : modules payants publiés, archive présente, lancement activé
        # (`oski.trial.enabled`). Inutile pour qui possède déjà le module.
        is_purchased = module.is_purchased_by(partner)
        Trial = request.env["oski.module.trial"].sudo()
        trial_versions = (
            Trial._trial_versions(module)
            if not is_purchased and Trial._is_enabled() else []
        )
        trial_url = ""
        if trial_versions:
            trial_version = version if version in trial_versions else (
                "20.0" if "20.0" in trial_versions else trial_versions[0]
            )
            trial_url = request.env["ir.http"]._url_for(
                "/apps/trial/start/%s?v=%s" % (module.id, trial_version)
            )
        return request.render(
            "oski_app_store.module_page",
            {
                "module": module,
                "version": version,
                "show_counters": request.env["oski.module"]._counters_settings()[0],
                "is_purchased": is_purchased,
                "trial_url": trial_url,
                "trial_versions": trial_versions,
                "is_sellable": is_sellable,
                "price_offer": price_offer,
                "buy_url": "/apps/buy/%s" % module.id if variant else "",
                "pill_versions": pill_versions,
                "upcoming_versions": upcoming_versions,
                # main_object : le titre de l'onglet, l'aperçu de partage et le
                # panneau de référencement de l'éditeur s'y accrochent.
                "main_object": module,
                "additional_title": module.name,
                "website_meta_description": module._seo_description(),
                "screenshots": module._screenshots_for_lang(request.env.lang),
                "back_url": self._catalog_back_url(),
                # Fiche d'une app : les suites qui l'installent (encart de vente).
                # Fiche d'une suite : son propre prix face aux apps une à une.
                "parent_suite_offers": self._suite_offers(module._published_suites_including()),
                "own_suite_offer": (
                    self._suite_offers(module)[0] if module.is_suite and module.is_published else None
                ),
            },
        )

    def _suite_offers(self, suites):
        """Une offre par suite : apps incluses, prix et économie.

        Les deux prix viennent de la liste de prix du site (le prix que le
        panier facturera, remise de lancement comprise) : la suite et ses apps
        sont comparées sur la même base. L'économie n'est donnée que si elle
        existe vraiment (≥ 5 %) — jamais de « −0 % » ni de suite plus chère
        affichée comme une affaire.
        """
        if not suites:
            return []
        website = request.website
        currency = website.currency_id
        pricelist = request.pricelist or request.env["product.pricelist"]
        rows = []
        products = request.env["product.product"].sudo()
        for suite in suites:
            members = suite._suite_members().filtered("is_published")
            paid = members.filtered(lambda m: not m.is_free)
            rows.append((suite, members, paid))
            for m in (suite | paid):
                if m.product_tmpl_id.product_variant_id:
                    products |= m.product_tmpl_id.product_variant_id
        prices = pricelist.sudo()._get_products_price(products, 1.0, currency=currency) if products else {}

        def _price(module):
            variant = module.product_tmpl_id.product_variant_id
            if variant and variant.id in prices:
                return prices[variant.id]
            return module.price or 0.0

        def _money(amount):
            return formatLang(request.env, amount, currency_obj=currency)

        offers = []
        for suite, members, paid in rows:
            price = _price(suite)
            separate = sum(_price(m) for m in paid)
            saving = round(100.0 * (1.0 - price / separate)) if separate else 0
            if saving < 5:
                saving, separate = 0, 0.0
            count = len(members)
            values = {
                "count": count, "price": _money(price),
                "separate": _money(separate), "saving": saving,
            }
            offers.append({
                "suite": suite,
                "count": count,
                "price": price,
                "separate": separate,
                "saving": saving,
                "price_label": values["price"],
                "separate_label": values["separate"] if separate else "",
                "apps_label": _("%(count)s apps included", **values),
                "saving_label": _("Save %(saving)s%%", **values) if saving else "",
                # Encart de la fiche d'une app de la suite.
                "pitch": (
                    _("%(count)s apps for %(price)s instead of %(separate)s "
                      "bought one by one.", **values) if saving
                    else _("%(count)s apps for %(price)s.", **values)
                ),
                # Fiche de la suite elle-même.
                "own_pitch": (
                    _("Bought one by one, these %(count)s apps cost %(separate)s: "
                      "the suite saves you %(saving)s%%.", **values) if saving else ""
                ),
            })
        return offers

    def _price_offer(self, product):
        """Remise de la liste de prix du site sur ce produit, ou None.

        La liste de prix est la seule source du prix payé : la fiche montre ce
        que le panier facturera (`_get_combination_info`, l'API des fiches
        produit de website_sale). Pourcentage et date de fin viennent de la
        règle appliquée, jamais d'un texte en dur. Sans remise → None, et la
        fiche garde son affichage habituel.
        """
        product = product.sudo()
        variant = product.product_variant_id
        if not variant:
            return None
        info = product._get_combination_info(product_id=variant.id)
        if not info.get("has_discounted_price"):
            return None
        pricelist = request.pricelist
        rule = request.env["product.pricelist.item"].sudo()
        if pricelist:
            _price, rule_id = pricelist._get_product_price_rule(variant, 1.0)
            rule = rule.browse(rule_id)
        list_price, price = info["list_price"], info["price"]
        if rule.compute_price == "percentage":
            percent = rule.percent_price
        else:
            percent = round(100.0 * (1.0 - price / list_price)) if list_price else 0
        percent_label = (
            "%d" % percent if float(percent).is_integer() else ("%s" % percent)
        )
        end = info.get("discount_end_date") or rule.date_end
        end_label = ""
        if end:
            locale = babel_locale_parse(request.env.lang or "en_US")
            end_label = babel_format_date(end.date(), format="long", locale=locale)
        if end_label:
            note = _(
                "Launch price — %(percent)s%% off until %(date)s",
                percent=percent_label,
                date=end_label,
            )
        else:
            note = _("Launch price — %(percent)s%% off", percent=percent_label)
        return {
            "list_price": list_price,
            "price": price,
            "currency": request.website.currency_id,
            "percent": percent,
            "date_end": end,
            "note": note,
        }

    @http.route(
        ["/apps/buy/<int:module_id>"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        website=True,
        sitemap=False,
    )
    def apps_buy(self, module_id, **kw):
        """Met le module au panier puis renvoie sur `/shop/cart`.

        En Odoo 19, `/shop/cart/update` est une route **jsonrpc en POST** : le
        lien GET que portait la fiche n'ajoutait rien et le visiteur voyait un
        panier vide, sans erreur. D'où cette route maison qui applique la même
        règle de vente que la fiche.

        Seul le **POST** (formulaire de la fiche, jeton CSRF vérifié par Odoo)
        remplit le panier. Quand le bouton était un lien GET, chaque robot qui
        le suivait ouvrait un panier : 1 882 devis anonymes en 11 jours, aucun
        humain derrière. Un GET (ancien lien, robot) renvoie sur la fiche sans
        rien créer.
        """
        module = request.env["oski.module"].sudo().browse(module_id).exists()
        if not module or not module.is_published:
            return request.not_found()
        if request.httprequest.method != "POST":
            return request.redirect(module.website_url, code=303)

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
        if not order_sudo.oski_geo_country_id:
            # Pays du clic, pour les paniers anonymes dont le client (« Public
            # user ») n'a pas de pays. Jamais d'adresse IP conservée.
            country = self._geoip_country()
            if country:
                order_sudo.oski_geo_country_id = country

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

    def _download_country(self, partner):
        """(pays, source) du téléchargement ; jamais d'adresse IP conservée.

        Pays du partenaire connecté s'il est renseigné, sinon géolocalisation
        de la requête (`request.geoip`). Sans base GeoLite2 sur le serveur,
        `country_code` vaut None : pays vide (« Inconnu »), sans erreur.
        """
        if partner:
            country = partner.country_id or partner.commercial_partner_id.country_id
            if country:
                return country, "partner"
        country = self._geoip_country()
        if country:
            return country, "geoip"
        return country, "unknown"

    def _geoip_country(self):
        """Pays de la requête par géolocalisation (GeoLite2), sinon vide.

        Jamais bloquant : sans base GeoLite2 ou sur une IP inconnue, renvoie un
        `res.country` vide. L'adresse IP n'est lue que pour ce calcul.
        """
        Country = request.env["res.country"].sudo()
        try:
            code = request.geoip.country_code
        except Exception:  # noqa: BLE001 — la géoloc ne doit jamais bloquer
            _logger.debug("Geolocation unavailable", exc_info=True)
            code = None
        if not code:
            return Country
        return Country.search([("code", "=", code.upper())], limit=1)

    def _log_download(self, version):
        """Trace le téléchargement servi (module, version, pays). Jamais bloquant."""
        try:
            user = request.env.user
            partner = user.partner_id if not user._is_public() else False
            country, source = self._download_country(partner)
            with request.env.cr.savepoint():
                request.env["oski.module.download"]._log(
                    version, partner=partner, country=country, source=source
                )
        except Exception:  # noqa: BLE001 — le visiteur doit recevoir son archive
            _logger.exception("Download %s not tracked", version.id)

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
            self._log_download(version)

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
