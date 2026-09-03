from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestMassEdit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.partners = cls.Partner.create([
            {"name": "Alpha"},
            {"name": "Bêta"},
        ])
        cls.Fields = cls.env["ir.model.fields"]

    def _wizard(self, field_name, records=None, **vals):
        records = records if records is not None else self.partners
        return self.env["oski.mass.edit.wizard"].with_context(
            active_model="res.partner", active_ids=records.ids,
        ).create(dict(
            model_name="res.partner",
            field_id=self.Fields._get("res.partner", field_name).id,
            **vals,
        ))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def test_config_creates_and_removes_binding(self):
        model = self.env["ir.model"]._get("res.partner")
        config = self.env["oski.mass.edit.config"].create({"model_id": model.id})
        self.assertTrue(config.action_id, "La configuration doit générer son action.")
        self.assertEqual(config.action_id.binding_model_id, model)
        self.assertEqual(config.action_id.binding_view_types, "list")
        self.assertEqual(config.action_id.res_model, "oski.mass.edit.wizard")
        action = config.action_id
        config.unlink()
        self.assertFalse(action.exists(), "L'action doit disparaître avec sa configuration.")

    def test_config_inactive_unbinds_without_losing_config(self):
        model = self.env["ir.model"]._get("res.partner")
        config = self.env["oski.mass.edit.config"].create({"model_id": model.id})
        config.active = False
        self.assertFalse(
            config.action_id.binding_model_id,
            "Désactiver retire l'entrée du menu Actions.",
        )
        self.assertTrue(config.action_id, "…mais conserve l'action et la configuration.")

    def test_config_refuses_transient_model(self):
        model = self.env["ir.model"]._get("oski.mass.edit.wizard")
        with self.assertRaises(UserError):
            self.env["oski.mass.edit.config"].create({"model_id": model.id})

    # ------------------------------------------------------------------
    # Écriture des valeurs
    # ------------------------------------------------------------------

    def test_default_get_reads_the_selection(self):
        wizard = self._wizard("ref")
        self.assertEqual(wizard.model_name, "res.partner")
        self.assertEqual(wizard.record_count, 2)

    def test_set_char_on_whole_selection(self):
        self._wizard("ref", value_char="REF-2026").action_apply()
        self.assertEqual(self.partners.mapped("ref"), ["REF-2026", "REF-2026"])

    def test_clear_empties_the_field(self):
        self.partners.write({"ref": "à effacer"})
        self._wizard("ref", operation="clear").action_apply()
        self.assertEqual(self.partners.mapped("ref"), [False, False])

    def test_set_boolean(self):
        self._wizard("employee", value_bool=True).action_apply()
        self.assertEqual(self.partners.mapped("employee"), [True, True])

    def test_set_integer(self):
        self._wizard("color", value_number=7).action_apply()
        self.assertEqual(self.partners.mapped("color"), [7, 7])

    def test_clear_integer_writes_zero(self):
        self.partners.write({"color": 5})
        self._wizard("color", operation="clear").action_apply()
        self.assertEqual(self.partners.mapped("color"), [0, 0])

    def test_set_many2one_through_reference(self):
        parent = self.Partner.create({"name": "Maison mère"})
        wizard = self._wizard("parent_id", value_reference="res.partner,%d" % parent.id)
        wizard.action_apply()
        self.assertEqual(self.partners.mapped("parent_id"), parent)

    def test_selection_hint_lists_the_keys(self):
        wizard = self._wizard("type")
        self.assertIn("contact", wizard.selection_hint or "")

    def test_set_selection(self):
        self._wizard("type", value_char="invoice").action_apply()
        self.assertEqual(self.partners.mapped("type"), ["invoice", "invoice"])

    # ------------------------------------------------------------------
    # Refus explicites
    # ------------------------------------------------------------------

    def test_invalid_selection_key_is_refused(self):
        wizard = self._wizard("type", value_char="pas-une-cle")
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertNotEqual(self.partners[0].type, "pas-une-cle")

    def test_reference_of_wrong_model_is_refused(self):
        user = self.env.ref("base.user_admin")
        wizard = self._wizard("parent_id", value_reference="res.users,%d" % user.id)
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_many2one_without_target_is_refused(self):
        with self.assertRaises(UserError):
            self._wizard("parent_id").action_apply()

    def test_unsupported_type_is_refused(self):
        wizard = self._wizard("category_id", value_char="x")
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_computed_field_is_refused(self):
        wizard = self._wizard("commercial_partner_id", value_char="x")
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_empty_selection_is_refused(self):
        wizard = self._wizard("ref", records=self.Partner, value_char="X")
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_write_goes_through_user_rights(self):
        """L'écriture reste soumise aux droits : aucun sudo dans l'assistant.

        Cible ``ir.ui.menu``, que tout utilisateur interne lit mais que seul un
        administrateur écrit — contrairement aux contacts, ouverts en écriture
        à tout le monde.
        """
        internal = self.env["res.users"].create({
            "name": "Interne", "login": "interne.masse@example.com",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        menu = self.env.ref("base.menu_custom")
        wizard = self.env["oski.mass.edit.wizard"].with_user(internal).with_context(
            active_model="ir.ui.menu", active_ids=menu.ids,
        ).create({
            "model_name": "ir.ui.menu",
            "field_id": self.Fields._get("ir.ui.menu", "name").id,
            "value_char": "Détourné",
        })
        with self.assertRaises(AccessError):
            wizard.action_apply()
        self.assertNotEqual(menu.name, "Détourné")
