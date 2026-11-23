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
    _description = "Barcode Generation"

    prefix = fields.Char(
        string="Prefix", required=True, default="200",
        help="Leading digits shared by all the generated codes. "
             "The 20-29 range is reserved for internal use.")
    scope = fields.Selection(
        [("empty", "All products without a barcode"),
         ("selected", "Selection only")],
        string="Scope", required=True, default="empty")
    limit = fields.Integer(
        string="At Most", default=500,
        help="Safeguard: maximum number of codes assigned in one go.")
    candidate_count = fields.Integer(
        string="Products Concerned", compute="_compute_candidate_count")
    generated_count = fields.Integer(string="Assigned Codes", readonly=True)

    @api.constrains("prefix")
    def _check_prefix(self):
        for wizard in self:
            # Pas de `strip()` ici : le préfixe sert tel quel à composer les
            # codes, un espace accepté finirait dans le code-barres.
            prefix = wizard.prefix or ""
            if not DIGITS.match(prefix):
                raise ValidationError(_(
                    "The prefix can only contain digits."))
            if not 1 <= len(prefix) <= 7:
                raise ValidationError(_(
                    "The prefix must be 1 to 7 digits long; beyond that, "
                    "there would not be enough room left to number the "
                    "products."))
            if prefix[0] == "0":
                raise ValidationError(_(
                    "An EAN-13 code never starts with zero."))

    @api.constrains("limit")
    def _check_limit(self):
        for wizard in self:
            if wizard.limit <= 0:
                raise ValidationError(_("The “At Most” safeguard must be positive."))

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
                    "The range of prefix %(prefix)s is exhausted: no free "
                    "number is left in it. Choose another prefix.",
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

    @api.model
    def _oski_taken_codes(self):
        """Tous les codes déjà en base : deux fiches ne peuvent pas porter le
        même. Les articles archivés comptent (les réactiver buterait sinon
        sur un doublon), comme les codes des conditionnements, que le cœur
        refuse de voir repris par un article."""
        products = self.env["product.product"].sudo().with_context(
            active_test=False).search_read(
                [("barcode", "!=", False)], ["barcode"], load="")
        taken = {row["barcode"] for row in products if row["barcode"]}
        if "product.packaging" in self.env:
            packagings = self.env["product.packaging"].sudo().search_read(
                [("barcode", "!=", False)], ["barcode"], load="")
            taken |= {row["barcode"] for row in packagings if row["barcode"]}
        return taken

    def action_generate(self):
        self.ensure_one()
        candidates = self._oski_candidates()[:self.limit]
        if not candidates:
            raise UserError(_(
                "Nothing to do: all the targeted products already have a "
                "barcode."))
        taken = self._oski_taken_codes()
        counter = 0
        for product in candidates:
            code, counter = self._oski_next_code(counter, taken)
            taken.add(code)
            product.barcode = code
        self.generated_count = len(candidates)
        return {
            "type": "ir.actions.act_window",
            "name": _("Barcoded Products"),
            "res_model": "product.product",
            "view_mode": "list,form",
            "views": [(self.env.ref(
                "oski_barcode_generator.view_oski_barcode_served_list").id, "list"),
                (False, "form")],
            "domain": [("id", "in", candidates.ids)],
            "context": {"create": False},
        }
