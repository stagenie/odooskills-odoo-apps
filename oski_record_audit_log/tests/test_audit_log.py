from odoo.tests.common import TransactionCase


class TestAuditLog(TransactionCase):
    """``TransactionCase.env`` tourne en superutilisateur, dont les gestes ne
    sont volontairement pas journalisés : tous les scénarios passent donc par
    un utilisateur réel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.Rule = cls.env["oski.audit.rule"]
        cls.Log = cls.env["oski.audit.log"]
        cls.user = cls.env["res.users"].create({
            "name": "Auditée", "login": "auditee@example.com",
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("base.group_partner_manager").id,
            ])],
        })
        cls.Partner = cls.env["res.partner"].with_user(cls.user)

    def _rule(self, **vals):
        return self.Rule.create(dict(model_id=self.partner_model.id, **vals))

    def _logs(self, operation=None, res_id=None):
        domain = [("model_name", "=", "res.partner")]
        if operation:
            domain.append(("operation", "=", operation))
        if res_id:
            domain.append(("res_id", "=", res_id))
        return self.Log.search(domain)

    # ------------------------------------------------------------------
    # Sans règle
    # ------------------------------------------------------------------

    def test_unwatched_model_writes_nothing(self):
        partner = self.Partner.create({"name": "Discret"})
        partner.write({"ref": "X"})
        partner.unlink()
        self.assertFalse(self._logs())

    # ------------------------------------------------------------------
    # Créations
    # ------------------------------------------------------------------

    def test_creation_is_logged_with_its_values(self):
        self._rule()
        partner = self.Partner.create({"name": "Nouvelle", "ref": "R-1"})
        log = self._logs("create", partner.id)
        self.assertEqual(len(log), 1)
        self.assertEqual(log.user_id, self.user)
        self.assertEqual(log.res_name, "Nouvelle")
        self.assertIn("R-1", log.changes)

    def test_batch_creation_logs_each_record(self):
        self._rule()
        partners = self.Partner.create([{"name": "B1"}, {"name": "B2"}])
        self.assertEqual(len(self._logs("create")), 2)
        self.assertEqual(
            set(self._logs("create").mapped("res_id")), set(partners.ids),
        )

    def test_creation_can_be_switched_off(self):
        self._rule(log_create=False)
        self.Partner.create({"name": "Muette"})
        self.assertFalse(self._logs("create"))

    # ------------------------------------------------------------------
    # Modifications
    # ------------------------------------------------------------------

    def test_write_records_before_and_after(self):
        self._rule()
        partner = self.Partner.create({"name": "Avant", "ref": "R-1"})
        partner.write({"ref": "R-2"})
        log = self._logs("write", partner.id)
        self.assertEqual(len(log), 1)
        self.assertIn("R-1", log.changes)
        self.assertIn("R-2", log.changes)
        self.assertIn("→", log.changes)

    def test_write_without_real_change_is_not_logged(self):
        self._rule()
        partner = self.Partner.create({"name": "Stable", "ref": "R"})
        partner.write({"ref": "R"})
        self.assertFalse(self._logs("write", partner.id))

    def test_field_filter_ignores_the_rest(self):
        field_ref = self.env["ir.model.fields"]._get("res.partner", "ref")
        self._rule(field_ids=[(6, 0, field_ref.ids)])
        partner = self.Partner.create({"name": "Filtrée"})
        partner.write({"comment": "sans intérêt"})
        self.assertFalse(self._logs("write", partner.id))
        partner.write({"ref": "compte"})
        self.assertEqual(len(self._logs("write", partner.id)), 1)

    def test_many2one_is_written_as_a_name(self):
        self._rule()
        parent = self.Partner.create({"name": "Maison mère"})
        child = self.Partner.create({"name": "Filiale"})
        child.write({"parent_id": parent.id})
        log = self._logs("write", child.id)
        self.assertIn("Maison mère", log.changes)

    def test_opaque_fields_are_skipped(self):
        self._rule()
        partner = self.Partner.create({"name": "Étiquetée"})
        tag = self.env["res.partner.category"].create({"name": "VIP"})
        partner.write({"category_id": [(6, 0, tag.ids)]})
        self.assertFalse(
            self._logs("write", partner.id),
            "Une liste liée n'a pas de valeur lisible sur une ligne de journal.",
        )

    # ------------------------------------------------------------------
    # Suppressions
    # ------------------------------------------------------------------

    def test_deletion_is_logged_before_it_happens(self):
        self._rule()
        partner = self.Partner.create({"name": "Condamnée"})
        partner_id = partner.id
        partner.unlink()
        log = self._logs("unlink", partner_id)
        self.assertEqual(len(log), 1)
        self.assertEqual(log.res_name, "Condamnée")

    # ------------------------------------------------------------------
    # Bornes
    # ------------------------------------------------------------------

    def test_superuser_is_not_logged(self):
        self._rule()
        self.env["res.partner"].create({"name": "Maintenance"})
        self.assertFalse(self._logs("create"))

    def test_the_journal_does_not_audit_itself(self):
        model_log = self.env["ir.model"]._get("oski.audit.log")
        self.Rule.create({"model_id": model_log.id})
        self._rule()
        self.Partner.create({"name": "Déclencheur"})
        self.assertFalse(
            self.Log.search([("model_name", "=", "oski.audit.log")]),
            "Écrire au journal ne doit pas produire de ligne de journal.",
        )

    def test_rule_change_takes_effect_immediately(self):
        rule = self._rule(log_create=False)
        self.Partner.create({"name": "Avant bascule"})
        self.assertFalse(self._logs("create"))
        rule.log_create = True
        self.Partner.create({"name": "Après bascule"})
        self.assertEqual(len(self._logs("create")), 1)
