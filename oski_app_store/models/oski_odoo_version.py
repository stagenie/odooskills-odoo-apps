from odoo import api, fields, models


class OskiOdooVersion(models.Model):
    _name = "oski.odoo.version"
    _description = "Version Odoo supportée par le store"
    _order = "sequence desc"

    name = fields.Char(string="Version", required=True)
    sequence = fields.Integer(string="Séquence", required=True, default=10)
    is_default = fields.Boolean(string="Version par défaut")

    _name_uniq = models.Constraint(
        "UNIQUE(name)", "Cette version Odoo est déjà déclarée."
    )

    @api.model
    def get_supported(self):
        """Noms des versions supportées, plus récente d'abord."""
        return self.search([]).mapped("name")

    @api.model
    def get_default(self):
        """Version par défaut du catalogue (flag, sinon plus haute séquence)."""
        rec = self.search([("is_default", "=", True)], limit=1)
        if not rec:
            rec = self.search([], limit=1)
        return rec.name or "19.0"
