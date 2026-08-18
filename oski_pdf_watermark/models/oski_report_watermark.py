import ast

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OskiReportWatermark(models.Model):
    """Une règle de filigrane : un rapport, une condition, un mot.

    La condition est un domaine évalué sur l'enregistrement imprimé, jamais
    du code : une règle mal écrite ne peut pas s'exécuter au moment de
    l'impression, elle est refusée dès l'enregistrement.
    """

    _name = "oski.report.watermark"
    _description = "Filigrane de rapport"
    _order = "sequence, id"

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    report_id = fields.Many2one(
        "ir.actions.report", string="Rapport", required=True, ondelete="cascade",
        domain=[("report_type", "in", ("qweb-pdf", "qweb-html"))])
    model_name = fields.Char(
        string="Modèle", related="report_id.model", readonly=True)
    filter_domain = fields.Char(
        string="Condition", default="[]",
        help="Domaine évalué sur l'enregistrement imprimé. Vide, la règle "
             "s'applique à toutes les impressions du rapport.")
    text = fields.Char(string="Mot", required=True, default="BROUILLON")
    color = fields.Char(string="Couleur", required=True, default="#B02A37")
    opacity = fields.Float(string="Opacité", default=0.12, digits=(3, 2))
    angle = fields.Integer(string="Inclinaison", default=-30)
    font_size = fields.Integer(string="Taille", default=90)
    company_id = fields.Many2one(
        "res.company", string="Société",
        help="Vide, la règle vaut pour toutes les sociétés.")

    @api.constrains("opacity")
    def _check_opacity(self):
        for rule in self:
            if not 0 < rule.opacity <= 1:
                raise ValidationError(_(
                    "L'opacité se donne entre 0 et 1 — 0,12 pour un filigrane "
                    "discret. Reçu : %s.", rule.opacity))

    @api.constrains("angle")
    def _check_angle(self):
        for rule in self:
            if not -90 <= rule.angle <= 90:
                raise ValidationError(_(
                    "L'inclinaison se donne entre -90 et 90 degrés. Reçu : %s.",
                    rule.angle))

    @api.constrains("font_size")
    def _check_font_size(self):
        for rule in self:
            if not 10 <= rule.font_size <= 400:
                raise ValidationError(_(
                    "La taille se donne entre 10 et 400 points. Reçu : %s.",
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
                    "La condition ne s'applique pas au modèle %(model)s : "
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
                    "La condition n'est pas un domaine lisible : %s", error))
            return []
        if not isinstance(domain, list):
            if raise_on_error:
                raise ValidationError(_(
                    "La condition doit être une liste, par exemple "
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
