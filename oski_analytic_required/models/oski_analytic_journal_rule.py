from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OskiAnalyticJournalRule(models.Model):
    """L'analytique obligatoire, journal par journal.

    Odoo sait déjà l'exiger par domaine d'activité, par préfixe de compte et
    par catégorie d'article, via l'applicabilité des plans analytiques. Il ne
    sait pas l'exiger **par journal** — or c'est ainsi que la plupart des
    cabinets raisonnent : tout ce qui passe par le journal des achats est
    ventilé, le reste ne l'est pas.
    """

    _name = "oski.analytic.journal.rule"
    _description = "Analytique obligatoire par journal"
    _order = "journal_id, id"
    _rec_name = "journal_id"

    journal_id = fields.Many2one(
        "account.journal", string="Journal", required=True, ondelete="cascade",
        index=True)
    account_prefix = fields.Char(
        string="Préfixes de comptes", default="",
        help="Limite l'exigence aux comptes dont le code commence par l'un de "
             "ces préfixes, séparés par des virgules. Vide : tous les comptes "
             "de résultat du journal.")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        "res.company", string="Société", related="journal_id.company_id",
        store=True, readonly=True)

    _unique_journal_prefix = models.Constraint(
        "UNIQUE(journal_id, account_prefix)",
        "Ce journal a déjà une règle pour ces préfixes.")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values["account_prefix"] = values.get("account_prefix") or ""
        return super().create(vals_list)

    def write(self, values):
        if "account_prefix" in values:
            # Deux NULL ne se ressemblent pas pour PostgreSQL : sans cette
            # normalisation, la contrainte d'unicité laisserait passer autant
            # de règles sans préfixe qu'on voudrait sur le même journal.
            values["account_prefix"] = values.get("account_prefix") or ""
        return super().write(values)

    @api.constrains("account_prefix")
    def _check_account_prefix(self):
        for rule in self:
            for prefix in rule._oski_prefixes():
                if not prefix.isdigit():
                    raise ValidationError(_(
                        "Un préfixe de compte ne contient que des chiffres : "
                        "« %s » n'en est pas un.", prefix))

    def _oski_prefixes(self):
        self.ensure_one()
        return [part.strip() for part in (self.account_prefix or "").split(",")
                if part.strip()]

    def _oski_covers(self, line):
        """Cette règle réclame-t-elle une ventilation sur cette ligne ?"""
        self.ensure_one()
        prefixes = self._oski_prefixes()
        if not prefixes:
            return True
        code = line.account_id.code or ""
        return any(code.startswith(prefix) for prefix in prefixes)
