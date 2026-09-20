from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OskiOdooVersion(models.Model):
    _name = "oski.odoo.version"
    _description = "Odoo version supported by the store"
    _order = "sequence desc"

    name = fields.Char(string="Version", required=True)
    sequence = fields.Integer(string="Sequence", required=True, default=10)
    is_default = fields.Boolean(string="Default version")
    is_upcoming = fields.Boolean(
        string="Upcoming",
        help="Odoo version not yet released: announced in the catalog "
             "and the selector, but without a downloadable archive.",
    )

    on_request = fields.Boolean(
        string="On request",
        help="Older Odoo version no longer followed by default: it stays in "
             "the selector, flagged 'on request', and is left out of the "
             "'for Odoo X and later' sentence.",
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)", "This Odoo version is already registered."
    )

    @api.constrains("is_upcoming", "on_request")
    def _check_upcoming_not_on_request(self):
        for version in self:
            if version.is_upcoming and version.on_request:
                raise ValidationError(_(
                    "Odoo %s cannot be both upcoming and on request.", version.name
                ))

    @api.model
    def get_supported(self):
        """Noms des versions du référentiel, plus récente d'abord (à venir incluse)."""
        return self.search([]).mapped("name")

    @api.model
    def get_released(self):
        """Versions réellement sorties, plus récente d'abord."""
        return self.search([("is_upcoming", "=", False)]).mapped("name")

    @api.model
    def get_standard(self):
        """Versions suivies d'office : sorties, et pas reléguées à la demande."""
        return self.search(
            [("is_upcoming", "=", False), ("on_request", "=", False)]
        ).mapped("name")

    @api.model
    def get_on_request(self):
        """Versions anciennes servies sur demande, plus récente d'abord."""
        return self.search([("on_request", "=", True)]).mapped("name")

    @api.model
    def get_upcoming(self):
        """Versions annoncées mais pas encore sorties, plus récente d'abord."""
        return self.search([("is_upcoming", "=", True)]).mapped("name")

    @api.model
    def get_default(self):
        """Version par défaut du catalogue (flag, sinon plus haute séquence).

        Jamais une version à venir : aucun module n'en propose d'archive, le
        catalogue s'ouvrirait sur un spectre entièrement éteint. Ni, tant
        qu'une version suivie existe, une version servie à la demande.
        """
        released = [("is_upcoming", "=", False)]
        standard = released + [("on_request", "=", False)]
        rec = self.search(standard + [("is_default", "=", True)], limit=1)
        if not rec:
            rec = self.search(standard, limit=1) or self.search(released, limit=1)
        return rec.name or "19.0"
