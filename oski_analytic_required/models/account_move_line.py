from odoo import api, fields, models

# Les contreparties ne portent jamais d'analytique : elles soldent l'écriture,
# elles ne consomment ni ne produisent rien.
COUNTERPART_TYPES = ("asset_receivable", "liability_payable")

def oski_wanted(operator, value):
    """Traduit une condition booléenne en « on cherche les vrais » ou non.

    Odoo 19 NORMALISE ``('champ', '=', True)`` en ``operator='in'`` et
    ``value=OrderedSet([True])`` avant d'appeler la méthode ``search`` d'un
    champ. Lire l'opérateur brut rendrait alors le complément exact du
    résultat attendu — une liste qui a l'air plausible et qui est fausse.
    """
    if operator in ("in", "not in"):
        truthy = any(bool(item) for item in value)
        return truthy if operator == "in" else not truthy
    if operator in ("=", "!="):
        return bool(value) if operator == "=" else not bool(value)
    raise NotImplementedError(
        "Unsupported operator on this field: %s" % operator)



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    oski_analytic_missing = fields.Boolean(
        string="Missing Analytic",
        compute="_compute_oski_analytic_missing",
        search="_search_oski_analytic_missing",
        help="True when a journal requires a distribution this line lacks. "
             "Not stored: the rule can change at any time, and a stored "
             "value would grow stale with nothing to refresh it.")

    def _oski_analytic_is_missing(self):
        self.ensure_one()
        # Une écriture comptabilisée ne bloque plus rien : la question ne se
        # pose que sur les brouillons, et c'est aussi ce qui borne l'écran de
        # contrôle à une population raisonnable.
        if self.parent_state != "draft":
            return False
        if self.analytic_distribution:
            return False
        if self.display_type in ("line_section", "line_note"):
            return False
        if self.tax_line_id or not self.account_id:
            return False
        if self.account_id.account_type in COUNTERPART_TYPES:
            return False
        rules = self.env["oski.analytic.journal.rule"].sudo().search([
            ("journal_id", "=", self.journal_id.id)])
        return any(rule._oski_covers(self) for rule in rules)

    def _compute_oski_analytic_missing(self):
        for line in self:
            line.oski_analytic_missing = line._oski_analytic_is_missing()

    @api.model
    def _search_oski_analytic_missing(self, operator, value):
        """La règle ne se réécrit pas en domaine, elle se rejoue.

        ``analytic_distribution`` est un champ JSON doté de sa propre méthode
        de recherche, qui ne comprend que « contient tel compte » : lui
        demander « est vide » rend un résultat silencieusement faux. Le tri
        final se fait donc en Python, sur une population déjà réduite par les
        seuls critères que la base sait filtrer.
        """
        rules = self.env["oski.analytic.journal.rule"].sudo().search([])
        ids = []
        if rules:
            candidates = self.sudo().search([
                ("journal_id", "in", rules.journal_id.ids),
                ("parent_state", "=", "draft"),
                ("tax_line_id", "=", False),
                ("display_type", "not in", ("line_section", "line_note")),
                ("account_id.account_type", "not in", list(COUNTERPART_TYPES)),
            ])
            ids = candidates.filtered(
                lambda line: line._oski_analytic_is_missing()).ids
        wanted = oski_wanted(operator, value)
        return [("id", "in" if wanted else "not in", ids)]
