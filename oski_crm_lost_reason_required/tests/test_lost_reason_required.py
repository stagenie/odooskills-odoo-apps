from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLostReasonRequired(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.oski_lost_reason_required = True
        cls.reason = cls.env["crm.lost.reason"].create({"name": "Prix trop élevé"})
        cls.other_reason = cls.env["crm.lost.reason"].create({"name": "Délai"})

    def _lead(self, name="Affaire", revenue=1000.0, **values):
        return self.env["crm.lead"].create(dict({
            "name": name, "type": "opportunity", "expected_revenue": revenue,
            "company_id": self.company.id,
        }, **values))

    # -- L'exigence -------------------------------------------------------

    def test_losing_without_a_reason_is_refused(self):
        lead = self._lead()
        with self.assertRaises(UserError):
            lead.action_set_lost()

    def test_losing_with_a_reason_works(self):
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.reason.id)
        self.assertEqual(lead.lost_reason_id, self.reason)
        self.assertFalse(lead.active)
        self.assertEqual(lead.probability, 0)

    def test_a_lead_that_already_carries_its_reason_passes(self):
        lead = self._lead(lost_reason_id=self.reason.id)
        lead.action_set_lost()
        self.assertFalse(lead.active)

    def test_the_rule_can_be_lifted_by_company(self):
        self.company.oski_lost_reason_required = False
        lead = self._lead()
        lead.action_set_lost()
        self.assertFalse(lead.active)
        self.assertFalse(lead.lost_reason_id)

    def test_the_refusal_names_every_offender(self):
        """Perdre en masse et se voir refuser sans savoir laquelle bloque
        obligerait à essayer une par une."""
        first = self._lead("Affaire A")
        second = self._lead("Affaire B")
        named = self._lead("Affaire C", lost_reason_id=self.reason.id)
        with self.assertRaises(UserError) as caught:
            (first | second | named).action_set_lost()
        message = str(caught.exception)
        self.assertIn("Affaire A", message)
        self.assertIn("Affaire B", message)
        self.assertNotIn("Affaire C", message)

    def test_the_leads_stay_open_when_the_batch_is_refused(self):
        lead = self._lead()
        with self.assertRaises(UserError):
            lead.action_set_lost()
        self.assertTrue(lead.active)

    # -- L'assistant ------------------------------------------------------

    def _wizard(self, leads):
        return self.env["crm.lead.lost"].create({"lead_ids": [(6, 0, leads.ids)]})

    def test_the_wizard_announces_the_requirement(self):
        wizard = self._wizard(self._lead())
        self.assertTrue(wizard.oski_reason_required)
        self.assertFalse(wizard.oski_feedback_required)

    def test_the_wizard_refuses_an_empty_reason(self):
        lead = self._lead()
        wizard = self._wizard(lead)
        with self.assertRaises(UserError):
            wizard.action_lost_reason_apply()

    def test_the_wizard_applies_the_reason(self):
        lead = self._lead()
        wizard = self._wizard(lead)
        wizard.lost_reason_id = self.reason
        wizard.action_lost_reason_apply()
        self.assertEqual(lead.lost_reason_id, self.reason)
        self.assertFalse(lead.active)

    def test_the_closing_note_can_be_demanded_too(self):
        self.company.oski_lost_feedback_required = True
        lead = self._lead()
        wizard = self._wizard(lead)
        wizard.lost_reason_id = self.reason
        self.assertTrue(wizard.oski_feedback_required)
        with self.assertRaises(UserError):
            wizard.action_lost_reason_apply()
        wizard.lost_feedback = "<p>Le client a retenu un concurrent local.</p>"
        wizard.action_lost_reason_apply()
        self.assertFalse(lead.active)

    # -- Ce que le motif coûte --------------------------------------------

    def test_a_reason_totals_what_it_took_away(self):
        self._lead("Grosse affaire", 200000.0).action_set_lost(
            lost_reason_id=self.reason.id)
        self._lead("Petite affaire", 1000.0).action_set_lost(
            lost_reason_id=self.reason.id)
        self._lead("Ailleurs", 5000.0).action_set_lost(
            lost_reason_id=self.other_reason.id)
        self.reason.invalidate_recordset()
        self.assertEqual(self.reason.oski_lost_revenue, 201000.0)
        self.assertEqual(self.other_reason.oski_lost_revenue, 5000.0)

    def test_lost_leads_are_archived_and_still_counted(self):
        """Perdre archive l'opportunité : un décompte qui l'ignorerait
        afficherait zéro partout."""
        lead = self._lead("Affaire", 4000.0)
        lead.action_set_lost(lost_reason_id=self.reason.id)
        self.assertFalse(lead.active)
        self.reason.invalidate_recordset()
        self.assertEqual(self.reason.oski_lost_revenue, 4000.0)
        self.assertTrue(self.reason.oski_last_lost_on)

    def test_a_reason_without_any_loss_shows_nothing(self):
        self.assertEqual(self.reason.oski_lost_revenue, 0.0)
        self.assertFalse(self.reason.oski_last_lost_on)

    def test_the_reason_opens_its_own_leads(self):
        lead = self._lead("Affaire", 4000.0)
        lead.action_set_lost(lost_reason_id=self.reason.id)
        action = self.reason.action_oski_open_leads()
        self.assertEqual(action["res_model"], "crm.lead")
        self.assertFalse(action["context"]["active_test"])
        found = self.env["crm.lead"].with_context(
            active_test=False).search(action["domain"])
        self.assertEqual(found, lead)
