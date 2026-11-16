from odoo import api, fields, models


class OskiModuleDownload(models.Model):
    """Un téléchargement réellement servi : module, version, pays.

    L'adresse IP n'est jamais stockée : seul le pays en est déduit, au moment
    du téléchargement (pays du partenaire connecté, sinon géolocalisation).
    """

    _name = "oski.module.download"
    _description = "Store download"
    _order = "date desc, id desc"
    _rec_name = "module_id"

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade", index=True
    )
    version_id = fields.Many2one(
        "oski.module.version", string="Archive", ondelete="set null"
    )
    odoo_version = fields.Char(
        string="Odoo version",
        help="Odoo version of the archive served, kept even if the archive is removed.",
    )
    module_version = fields.Char(string="Module version")
    date = fields.Datetime(
        string="Date", required=True, default=fields.Datetime.now, index=True
    )
    is_free = fields.Boolean(string="Open source")
    pricing = fields.Selection(
        [("free", "Open source"), ("paid", "Paid")],
        string="Pricing",
        compute="_compute_pricing",
        store=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", ondelete="set null", index=True
    )
    country_id = fields.Many2one(
        "res.country", string="Country", ondelete="set null", index=True
    )
    country_source = fields.Selection(
        [
            ("partner", "Customer address"),
            ("geoip", "Geolocation"),
            ("unknown", "Unknown"),
        ],
        string="Country source",
        default="unknown",
        required=True,
    )

    @api.depends("is_free")
    def _compute_pricing(self):
        for record in self:
            record.pricing = "free" if record.is_free else "paid"

    @api.model
    def _log(self, version, partner=False, country=False, source="unknown"):
        """Crée la ligne de téléchargement (sudo : l'appelant est souvent public)."""
        module = version.module_id
        return self.sudo().create(
            {
                "module_id": module.id,
                "version_id": version.id,
                "odoo_version": version.odoo_version,
                "module_version": version.module_version,
                "is_free": module.is_free,
                "partner_id": partner.id if partner else False,
                "country_id": country.id if country else False,
                "country_source": source if country else "unknown",
            }
        )
