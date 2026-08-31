from odoo import api, fields, models


class OskiModule(models.Model):
    _name = "oski.module"
    _description = "Module du store OdooSkills"
    _inherit = ["website.published.mixin"]
    _order = "name"

    name = fields.Char(string="Nom affiché", required=True, translate=True)
    technical_name = fields.Char(string="Nom technique", required=True)
    summary = fields.Char(string="Résumé", translate=True)
    # sanitize=False requis : la doc importée (format apps.odoo.com) repose sur des
    # styles inline que le sanitizer dégraderait. Écriture réservée aux managers
    # (ACL) + scripts de seed — ne jamais exposer en écriture portail/public.
    description_html = fields.Html(string="Description", translate=True, sanitize=False)
    category_id = fields.Many2one("oski.module.category", string="Catégorie")
    license = fields.Selection(
        [("lgpl-3", "LGPL-3"), ("opl-1", "OPL-1"), ("other", "Propriétaire")],
        string="Licence",
        default="lgpl-3",
        required=True,
    )
    is_free = fields.Boolean(string="Gratuit", default=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        default=lambda self: self.env.ref("base.USD", raise_if_not_found=False),
    )
    price = fields.Monetary(
        string="Prix",
        currency_field="currency_id",
        help="Prix de vente du module premium (issu du manifeste). Vide si gratuit.",
    )
    author = fields.Char(string="Auteur", default="OdooSkills")
    maintainer = fields.Char(string="Mainteneur", default="ADICOPS")
    version_line_ids = fields.One2many(
        "oski.module.version", "module_id", string="Versions"
    )
    dependency_ids = fields.Many2many(
        "oski.module",
        "oski_module_dependency_rel",
        "module_id",
        "dependency_id",
        string="Dépendances",
    )
    tag_ids = fields.Many2many(
        "oski.module.tag",
        "oski_module_tag_rel",
        "module_id",
        "tag_id",
        string="Tags",
    )
    image_1920 = fields.Image(string="Icône")
    screenshot_ids = fields.Many2many(
        "ir.attachment",
        "oski_module_screenshot_rel",
        "module_id",
        "attachment_id",
        string="Captures d'écran",
        help="Images de la galerie de la fiche publique (attachments publics).",
    )
    product_tmpl_id = fields.Many2one(
        "product.template", string="Produit lié", ondelete="restrict", copy=False
    )

    _technical_name_uniq = models.Constraint(
        "UNIQUE(technical_name)",
        "Le nom technique du module doit être unique.",
    )

    def _compute_website_url(self):
        for record in self:
            if record.id:
                record.website_url = "/apps/%s" % self.env["ir.http"]._slug(record)
            else:
                record.website_url = "#"

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
