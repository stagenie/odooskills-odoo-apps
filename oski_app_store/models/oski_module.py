from odoo import _, api, fields, models


class OskiModule(models.Model):
    _name = "oski.module"
    _description = "OdooSkills store module"
    _inherit = ["website.published.mixin", "website.seo.metadata"]
    _order = "name"

    name = fields.Char(string="Display name", required=True, translate=True)
    technical_name = fields.Char(string="Technical name", required=True)
    summary = fields.Char(string="Summary", translate=True)
    # sanitize=False requis : la doc importée (format apps.odoo.com) repose sur des
    # styles inline que le sanitizer dégraderait. Écriture réservée aux managers
    # (ACL) + scripts de seed — ne jamais exposer en écriture portail/public.
    description_html = fields.Html(string="Description", translate=True, sanitize=False)
    category_id = fields.Many2one("oski.module.category", string="Category")
    license = fields.Selection(
        [("lgpl-3", "LGPL-3"), ("opl-1", "OPL-1"), ("other", "Proprietary")],
        string="License",
        default="lgpl-3",
        required=True,
    )
    is_free = fields.Boolean(string="Free", default=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.ref("base.USD", raise_if_not_found=False),
    )
    price = fields.Monetary(
        string="Price",
        currency_field="currency_id",
        help="Sale price of the premium module (from the manifest). Empty when free.",
    )
    author = fields.Char(string="Author", default="OdooSkills")
    maintainer = fields.Char(string="Maintainer", default="ADICOPS")
    version_line_ids = fields.One2many(
        "oski.module.version", "module_id", string="Versions"
    )
    dependency_ids = fields.Many2many(
        "oski.module",
        "oski_module_dependency_rel",
        "module_id",
        "dependency_id",
        string="Dependencies",
    )
    tag_ids = fields.Many2many(
        "oski.module.tag",
        "oski_module_tag_rel",
        "module_id",
        "tag_id",
        string="Tags",
    )
    image_1920 = fields.Image(string="Icon")
    screenshot_ids = fields.Many2many(
        "ir.attachment",
        "oski_module_screenshot_rel",
        "module_id",
        "attachment_id",
        string="Screenshots",
        help="Public gallery images of the module page (public attachments).",
    )
    product_tmpl_id = fields.Many2one(
        "product.template", string="Linked product", ondelete="restrict", copy=False
    )
    download_count = fields.Integer(
        string="Downloads",
        compute="_compute_download_count",
        help="Number of times any archive of this module was served, summed across versions.",
    )
    purchase_count = fields.Integer(
        string="Purchases",
        compute="_compute_purchase_count",
        help="Number of distinct customers with a confirmed order for this module.",
    )

    _technical_name_uniq = models.Constraint(
        "UNIQUE(technical_name)",
        "The module technical name must be unique.",
    )

    @api.depends("version_line_ids.download_count")
    def _compute_download_count(self):
        for record in self:
            record.download_count = sum(record.version_line_ids.mapped("download_count"))

    @api.depends("product_tmpl_id", "is_free")
    def _compute_purchase_count(self):
        # Non stocké : @api.depends ne sert qu'à invalider le cache, pas à
        # dériver une formule de stockage.
        paid = self.filtered(lambda m: not m.is_free and m.product_tmpl_id)
        (self - paid).purchase_count = 0
        if not paid:
            return

        templates = paid.product_tmpl_id
        Line = self.env["sale.order.line"].sudo()
        # Un seul _read_group pour tous les modules du batch : grouper
        # directement sur `product_id.product_tmpl_id` n'est pas supporté,
        # on groupe donc sur (product_id, order_partner_id) et on reconstitue
        # le gabarit en Python — un seul aller-retour, avec prefetch en lot.
        groups = Line._read_group(
            [
                ("product_id.product_tmpl_id", "in", templates.ids),
                ("state", "=", "sale"),
            ],
            ["product_id", "order_partner_id"],
            [],
        )

        products = self.env["product.product"].browse(
            {product.id for product, partner in groups if product and partner}
        )
        tmpl_id_by_product_id = {p.id: p.product_tmpl_id.id for p in products}

        partner_ids_by_tmpl_id = {}
        for product, partner in groups:
            if not product or not partner:
                continue
            tmpl_id = tmpl_id_by_product_id.get(product.id)
            if not tmpl_id:
                continue
            partner_ids_by_tmpl_id.setdefault(tmpl_id, set()).add(partner.id)

        for record in paid:
            record.purchase_count = len(
                partner_ids_by_tmpl_id.get(record.product_tmpl_id.id, ())
            )

    def _compute_website_url(self):
        # The slug comes from the technical name: the same URL in English and
        # in French, a single canonical for search engines. ir.http._slug is
        # overridden in ir_http.py to slug oski.module by technical_name, so
        # the frontend canonical redirect (_pre_dispatch) agrees with this URL.
        for record in self:
            if record.id:
                record.website_url = "/apps/%s" % self.env["ir.http"]._slug(record)
            else:
                record.website_url = "#"

    @api.model
    def _counters_settings(self):
        """(show, minimum) : réglages `ir.config_parameter` du store."""
        Param = self.env["ir.config_parameter"].sudo()
        show = Param.get_param("oski_app_store.show_counters", "False") == "True"
        try:
            minimum = int(Param.get_param("oski_app_store.counters_min", "10"))
        except ValueError:
            minimum = 10
        return show, minimum

    def counters_visible(self, kind):
        """True si le compteur `kind` ('download' | 'purchase') doit s'afficher."""
        self.ensure_one()
        show, minimum = self._counters_settings()
        value = self.download_count if kind == "download" else self.purchase_count
        return show and value >= minimum

    def _default_website_meta(self):
        """Titre, description et image de partage propres à chaque module.

        Sans cela, un lien de fiche collé dans une conversation affiche le nom
        du site et son logo : cent quarante-sept aperçus identiques.
        """
        res = super()._default_website_meta()
        opengraph, twitter = res["default_opengraph"], res["default_twitter"]
        opengraph["og:title"] = twitter["twitter:title"] = self.name
        if self.summary:
            opengraph["og:description"] = self.summary
            twitter["twitter:description"] = self.summary
        if self.image_1920:
            image_url = "/web/image/oski.module/%s/image_1920" % self.id
            opengraph["og:image"] = twitter["twitter:image"] = image_url
        return res

    def _seo_description(self):
        """Méta-description : le résumé, sinon le nom. Jamais vide."""
        self.ensure_one()
        return self.summary or _("%s — an Odoo module by OdooSkills.") % self.name

    def latest_version(self, odoo_version="19.0"):
        """Retourne la dernière oski.module.version pour une version Odoo."""
        self.ensure_one()
        return self.version_line_ids.filtered(
            lambda v: v.odoo_version == odoo_version
        )[:1]

    def available_versions(self):
        """Set des versions Odoo pour lesquelles ce module a une archive."""
        self.ensure_one()
        return set(self.version_line_ids.mapped("odoo_version"))

    def supports(self, odoo_version):
        """True si le module a une archive pour cette version Odoo."""
        self.ensure_one()
        return odoo_version in self.available_versions()

    def download_target(self, selected):
        """Version à servir : exacte si supportée, sinon dernière dispo.

        Retourne un recordset oski.module.version (vide si aucune version).
        """
        self.ensure_one()
        exact = self.version_line_ids.filtered(
            lambda v: v.odoo_version == selected
        )
        if exact:
            return exact[:1]
        return self.version_line_ids.sorted(
            lambda v: v.odoo_version_id.sequence, reverse=True
        )[:1]

    def is_purchased_by(self, partner):
        """True si ce partenaire détient une commande confirmée pour ce module.

        Même règle que le contrôleur de téléchargement : le droit naît de la
        commande confirmée (`state == 'sale'`), pas du devis. En vente en ligne
        la commande ne se confirme qu'au paiement réussi.
        """
        self.ensure_one()
        if self.is_free:
            return True
        if not partner or not self.product_tmpl_id:
            return False
        return bool(
            self.env["sale.order.line"]
            .sudo()
            .search_count(
                [
                    ("order_partner_id", "=", partner.id),
                    ("product_id.product_tmpl_id", "=", self.product_tmpl_id.id),
                    ("state", "=", "sale"),
                ]
            )
        )

    @api.model
    def purchased_by(self, partner):
        """Modules payants dont ce partenaire a une commande confirmée."""
        if not partner:
            return self.browse()
        lines = (
            self.env["sale.order.line"]
            .sudo()
            .search([("order_partner_id", "=", partner.id), ("state", "=", "sale")])
        )
        templates = lines.mapped("product_id.product_tmpl_id")
        if not templates:
            return self.browse()
        return self.sudo().search([("product_tmpl_id", "in", templates.ids)])

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_screenshots_public()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "screenshot_ids" in vals:
            self._sync_screenshots_public()
        return res

    def _sync_screenshots_public(self):
        """Les captures de la galerie publique doivent être servies aux visiteurs."""
        shots = self.sudo().screenshot_ids.filtered(lambda a: not a.public)
        if shots:
            shots.write({"public": True})
