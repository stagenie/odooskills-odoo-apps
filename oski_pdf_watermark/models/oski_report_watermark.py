import ast
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# La couleur est recopiée telle quelle dans l'attribut ``style`` du rapport :
# seule une notation hexadécimale y entre, jamais une déclaration CSS de plus
# (``red;background:url(...)`` ferait charger une adresse externe au moteur
# d'impression).
HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


class OskiReportWatermark(models.Model):
    """Une règle de filigrane : un rapport, une condition, un mot.

    La condition est un domaine évalué sur l'enregistrement imprimé, jamais
    du code : une règle mal écrite ne peut pas s'exécuter au moment de
    l'impression, elle est refusée dès l'enregistrement.
    """

    _name = "oski.report.watermark"
    _description = "Report Watermark"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    report_id = fields.Many2one(
        "ir.actions.report", string="Report", required=True, ondelete="cascade",
        domain=[("report_type", "in", ("qweb-pdf", "qweb-html"))])
    model_name = fields.Char(
        string="Model", related="report_id.model", readonly=True)
    filter_domain = fields.Char(
        string="Condition", default="[]",
        help="Domain evaluated on the printed record. Empty, the rule "
             "applies to every print of the report.")
    text = fields.Char(string="Word", required=True, default=lambda self: self.env._("DRAFT"))
    color = fields.Char(string="Color", required=True, default="#B02A37")
    opacity = fields.Float(string="Opacity", default=0.12, digits=(3, 2))
    angle = fields.Integer(string="Angle", default=-30)
    font_size = fields.Integer(string="Size", default=90)
    company_id = fields.Many2one(
        "res.company", string="Company",
        help="Empty, the rule applies to all companies.")

    @api.constrains("opacity")
    def _check_opacity(self):
        for rule in self:
            if not 0 < rule.opacity <= 1:
                raise ValidationError(_(
                    "The opacity must be between 0 and 1 — 0.12 for a "
                    "discreet watermark. Received: %s.", rule.opacity))

    @api.constrains("color")
    def _check_color(self):
        for rule in self:
            if not HEX_COLOR.match(rule.color or ""):
                raise ValidationError(_(
                    "The color must be hexadecimal, for example #B02A37. "
                    "Received: %s.", rule.color))

    @api.constrains("angle")
    def _check_angle(self):
        for rule in self:
            if not -90 <= rule.angle <= 90:
                raise ValidationError(_(
                    "The angle must be between -90 and 90 degrees. Received: %s.",
                    rule.angle))

    @api.constrains("font_size")
    def _check_font_size(self):
        for rule in self:
            if not 10 <= rule.font_size <= 400:
                raise ValidationError(_(
                    "The size must be between 10 and 400 points. Received: %s.",
                    rule.font_size))

    @api.constrains("filter_domain", "report_id")
    def _check_filter_domain(self):
        """Refuse à l'enregistrement ce qui casserait à l'impression.

        Un domaine invalide découvert au moment d'imprimer ferait échouer
        l'impression elle-même : autant le dire tout de suite, ici, où
        l'auteur de la règle est devant l'écran.
        """
        for rule in self:
            domain = rule._oski_domain(raise_on_error=True)
            model = rule.report_id.model
            if not domain or not model or model not in self.env:
                continue
            try:
                self.env[model].search_count(domain, limit=1)
            except Exception as error:
                raise ValidationError(_(
                    "The condition does not apply to model %(model)s: "
                    "%(error)s", model=model, error=error))

    def _oski_domain(self, raise_on_error=False):
        self.ensure_one()
        raw = (self.filter_domain or "").strip()
        if not raw:
            return []
        try:
            domain = ast.literal_eval(raw)
        except (SyntaxError, ValueError) as error:
            if raise_on_error:
                raise ValidationError(_(
                    "The condition is not a readable domain: %s", error))
            return []
        if not isinstance(domain, list):
            if raise_on_error:
                raise ValidationError(_(
                    "The condition must be a list, for example "
                    "[('state', '=', 'draft')]."))
            return []
        return domain

    def _oski_values(self):
        """Ce que le gabarit reçoit — jamais l'enregistrement lui-même."""
        self.ensure_one()
        return {
            "text": self.text,
            "color": self.color,
            "opacity": self.opacity,
            "angle": self.angle,
            "font_size": self.font_size,
        }
