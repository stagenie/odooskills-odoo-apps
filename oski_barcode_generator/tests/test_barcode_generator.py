from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools.barcode import check_barcode_encoding


@tagged("post_install", "-at_install")
class TestBarcodeGenerator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Les articles de démonstration porteraient leurs propres codes et
        # fausseraient les décomptes : la portée est toujours explicite ici.
        cls.products = cls.env["product.product"].create([
            {"name": "Article %s" % index, "type": "consu"} for index in range(3)])
        cls.coded = cls.env["product.product"].create({
            "name": "Déjà étiqueté", "type": "consu", "barcode": "2001234567895"})

    def _wizard(self, products=None, **values):
        context = {}
        if products is not None:
            context = {"active_model": "product.product", "active_ids": products.ids}
            values.setdefault("scope", "selected")
        return self.env["oski.barcode.generator"].with_context(**context).create(values)

    def test_every_product_gets_a_valid_ean13(self):
        wizard = self._wizard(self.products)
        wizard.action_generate()
        for product in self.products:
            self.assertTrue(product.barcode)
            self.assertTrue(
                check_barcode_encoding(product.barcode, "ean13"),
                "%s n'est pas un EAN13 valide" % product.barcode)

    def test_the_codes_carry_the_prefix(self):
        wizard = self._wizard(self.products, prefix="255")
        wizard.action_generate()
        for product in self.products:
            self.assertTrue(product.barcode.startswith("255"))
            self.assertEqual(len(product.barcode), 13)

    def test_the_codes_are_all_different(self):
        wizard = self._wizard(self.products)
        wizard.action_generate()
        codes = self.products.mapped("barcode")
        self.assertEqual(len(set(codes)), len(codes))

    def test_a_product_already_labelled_is_never_touched(self):
        """Écraser un code casserait les étiquettes déjà imprimées."""
        wizard = self._wizard(self.products | self.coded)
        wizard.action_generate()
        self.assertEqual(self.coded.barcode, "2001234567895")

    def test_a_code_already_taken_is_skipped(self):
        """Une base peut porter des codes importés qui tombent dans la plage."""
        taken = self.env["product.product"].create({
            "name": "Importé", "type": "consu", "barcode": "2000000000018"})
        wizard = self._wizard(self.products)
        wizard.action_generate()
        self.assertNotIn(taken.barcode, self.products.mapped("barcode"))
        self.assertEqual(taken.barcode, "2000000000018")

    def test_the_wizard_counts_before_acting(self):
        wizard = self._wizard(self.products)
        self.assertEqual(wizard.candidate_count, 3)
        wizard.action_generate()
        self.assertEqual(wizard.generated_count, 3)

    def test_the_guard_rail_caps_the_batch(self):
        wizard = self._wizard(self.products, limit=2)
        wizard.action_generate()
        served = self.products.filtered("barcode")
        self.assertEqual(len(served), 2)

    def test_nothing_to_do_is_said_out_loud(self):
        wizard = self._wizard(self.coded)
        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_the_whole_catalogue_can_be_served_at_once(self):
        wizard = self._wizard(scope="empty", limit=10000)
        self.assertGreaterEqual(wizard.candidate_count, 3)
        wizard.action_generate()
        self.assertFalse(self.products.filtered(lambda p: not p.barcode))
        self.assertFalse(self.env["product.product"].search(
            [("barcode", "=", False)]))

    def test_a_template_selection_serves_its_variants(self):
        template = self.env["product.template"].create({
            "name": "Article à variantes", "type": "consu"})
        wizard = self.env["oski.barcode.generator"].with_context(
            active_model="product.template",
            active_ids=template.ids).create({"scope": "selected"})
        wizard.action_generate()
        self.assertTrue(template.product_variant_id.barcode)

    def test_the_action_shows_what_was_served(self):
        wizard = self._wizard(self.products)
        action = wizard.action_generate()
        self.assertEqual(action["res_model"], "product.product")
        found = self.env["product.product"].search(action["domain"])
        self.assertEqual(found, self.products)

    def test_a_prefix_must_be_digits(self):
        with self.assertRaises(ValidationError):
            self._wizard(self.products, prefix="ABC")

    def test_a_prefix_never_starts_with_zero(self):
        with self.assertRaises(ValidationError):
            self._wizard(self.products, prefix="012")

    def test_a_prefix_too_long_leaves_no_room(self):
        with self.assertRaises(ValidationError):
            self._wizard(self.products, prefix="20012345")

    def test_the_guard_rail_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._wizard(self.products, limit=0)

    def test_an_exhausted_range_is_said_out_loud(self):
        """Un préfixe de sept chiffres ne laisse que cinq chiffres de
        numérotation : la plage se vide, et il faut le dire plutôt que
        boucler."""
        wizard = self._wizard(self.products, prefix="2001234")
        taken = {"x"}
        counter = 10 ** 5 - 1
        with self.assertRaises(UserError):
            wizard._oski_next_code(counter, taken)
