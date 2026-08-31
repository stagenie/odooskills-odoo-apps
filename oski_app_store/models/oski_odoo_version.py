from odoo import api, fields, models


class OskiOdooVersion(models.Model):
    _name = "oski.odoo.version"
    _description = "Version Odoo supportée par le store"
    _order = "sequence desc"

    name = fields.Char(string="Version", required=True)
    sequence = fields.Integer(string="Séquence", required=True, default=10)
    is_default = fields.Boolean(string="Version par défaut")
    is_upcoming = fields.Boolean(
        string="À venir",
        help="Version Odoo pas encore sortie : annoncée dans le catalogue "
             "et le sélecteur, mais sans archive téléchargeable.",
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)", "Cette version Odoo est déjà déclarée."
    )

    @api.model
    def get_supported(self):
        """Noms des versions du référentiel, plus récente d'abord (à venir incluse)."""
        return self.search([]).mapped("name")

    @api.model
    def get_released(self):
        """Versions réellement sorties, plus récente d'abord."""
        return self.search([("is_upcoming", "=", False)]).mapped("name")

    @api.model
    def get_upcoming(self):
        """Versions annoncées mais pas encore sorties, plus récente d'abord."""
        return self.search([("is_upcoming", "=", True)]).mapped("name")

    @api.model
    def get_default(self):
        """Version par défaut du catalogue (flag, sinon plus haute séquence).

        Jamais une version à venir : aucun module n'en propose d'archive, le
        catalogue s'ouvrirait sur un spectre entièrement éteint.
        """
        released = [("is_upcoming", "=", False)]
        rec = self.search(released + [("is_default", "=", True)], limit=1)
        if not rec:
            rec = self.search(released, limit=1)
        return rec.name or "19.0"
