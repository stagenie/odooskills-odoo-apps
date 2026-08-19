import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.barcode import check_barcode_encoding, get_barcode_check_digit

DIGITS = re.compile(r"^\d+$")
EAN13_LENGTH = 13


class OskiBarcodeGenerator(models.TransientModel):
    """Attribution de codes EAN13 à des articles qui n'en ont pas.

    Le préfixe par défaut commence par 2 : la plage 20-29 est celle que la
    norme réserve à l'usage interne d'une entreprise. Y déroger produirait
    des codes qui ressemblent à ceux d'un autre fabricant.
    """

    _name = "oski.barcode.generator"
    _description = "Génération de codes-barres"

    prefix = fields.Char(
        string="Préfixe", required=True, default="200",
        help="Chiffres de tête, communs à tous les codes produits. "
             "La plage 20-29 est réservée à l'usage interne.")
    scope = fields.Selection(
        [("empty", "Tous les articles sans code-barres"),
         ("selected", "Uniquement la sélection")],
        string="Portée", required=True, default="empty")
    limit = fields.Integer(
        string="Au plus", default=500,
        help="Garde-fou : nombre maximal de codes attribués en une fois.")
    candidate_count = fields.Integer(
        string="Articles concernés", compute="_compute_candidate_count")
    generated_count = fields.Integer(string="Codes attribués", readonly=True)

    @api.constrains("prefix")
    def _check_prefix(self):
        for wizard in self:
            prefix = (wizard.prefix or "").strip()
            if not DIGITS.match(prefix):
                raise ValidationError(_(
                    "Le préfixe ne peut contenir que des chiffres."))
            if not 1 <= len(prefix) <= 7:
                raise ValidationError(_(
                    "Le préfixe tient entre 1 et 7 chiffres ; au-delà il ne "
                    "resterait pas assez de place pour numéroter les articles."))
            if prefix[0] == "0":
                raise ValidationError(_(
                    "Un EAN13 ne commence pas par zéro."))

    @api.constrains("limit")
    def _check_limit(self):
        for wizard in self:
            if wizard.limit <= 0:
                raise ValidationError(_("Le garde-fou doit être positif."))

    @api.depends("scope")
    def _compute_candidate_count(self):
        for wizard in self:
            wizard.candidate_count = len(wizard._oski_candidates())

    def _oski_candidates(self):
        """Les articles à servir : toujours ceux qui n'ont PAS de code.

        Écraser un code-barres existant casserait les étiquettes déjà
        imprimées et les scanners qui les lisent : ce n'est jamais proposé.
        """
        self.ensure_one()
        products = self.env["product.product"]
        if self.scope == "selected":
            model = self.env.context.get("active_model")
            ids = self.env.context.get("active_ids") or []
            if model == "product.template":
                products = self.env["product.template"].browse(
                    ids).product_variant_ids
            elif model == "product.product":
                products = products.browse(ids)
            products = products.exists()
        else:
            products = products.search([("barcode", "=", False)])
        return products.filtered(lambda product: not product.barcode)

    def _oski_next_code(self, counter, taken):
        """Rend le prochain code libre, et le compteur qui suit.

        Les codes déjà pris sont sautés : une base peut porter des codes
        importés qui tombent dans la même plage.
        """
        body_length = EAN13_LENGTH - 1 - len(self.prefix)
        while True:
            counter += 1
            if counter >= 10 ** body_length:
                raise UserError(_(
                    "La plage du préfixe %(prefix)s est épuisée : il n'y reste "
                    "aucun numéro libre. Choisissez un autre préfixe.",
                    prefix=self.prefix))
            body = str(counter).zfill(body_length)
            # `get_barcode_check_digit` RETIRE le dernier caractère avant de
            # calculer : il attend le code ENTIER, pas les douze premiers
            # chiffres. Lui passer le corps seul décalerait tout le calcul.
            code = "%s%s%s" % (
                self.prefix, body,
                get_barcode_check_digit("%s%s0" % (self.prefix, body)))
            if code not in taken:
                return code, counter

    def action_generate(self):
        self.ensure_one()
        candidates = self._oski_candidates()[:self.limit]
        if not candidates:
            raise UserError(_(
                "Aucun article à servir : tous ceux visés portent déjà un "
                "code-barres."))
        # Tous les codes déjà en base, y compris ceux des articles hors
        # sélection : deux articles ne peuvent pas porter le même.
        rows = self.env["product.product"].sudo().search_read(
            [("barcode", "!=", False)], ["barcode"], load="")
        taken = {row["barcode"] for row in rows if row["barcode"]}
        counter = 0
        for product in candidates:
            code, counter = self._oski_next_code(counter, taken)
            taken.add(code)
            product.barcode = code
        self.generated_count = len(candidates)
        return {
            "type": "ir.actions.act_window",
            "name": _("Articles servis"),
            "res_model": "product.product",
            "view_mode": "list,form",
            "domain": [("id", "in", candidates.ids)],
            "context": {"create": False},
        }
