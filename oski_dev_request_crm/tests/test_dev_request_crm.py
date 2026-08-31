from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDevRequestCrm(TransactionCase):
    """Une demande de module est d'abord une affaire à gagner."""

    def _make_request(self, **kw):
        vals = {
            "requester_name": "Awa Diop",
            "company_name": "Atelier Nord",
            "email": "awa@example.com",
            "phone": "+213 555 00 11 22",
            "subject": "Module de suivi des tournées",
            "description": "Planifier les tournées et relever les compteurs.",
        }
        vals.update(kw)
        return self.env["oski.dev.request"].create(vals)

    def test_request_opens_an_opportunity(self):
        request = self._make_request()
        self.assertTrue(request.lead_id, "aucune opportunité ouverte")
        self.assertEqual(request.lead_id.type, "opportunity")

    def test_contact_details_travel_to_the_lead(self):
        request = self._make_request()
        lead = request.lead_id
        self.assertEqual(lead.contact_name, "Awa Diop")
        self.assertEqual(lead.partner_name, "Atelier Nord")
        self.assertEqual(lead.email_from, "awa@example.com")
        self.assertEqual(lead.name, "Module de suivi des tournées")

    def test_need_is_readable_in_the_lead(self):
        request = self._make_request()
        body = request.lead_id.description or ""
        self.assertIn("relever les compteurs", body)
        self.assertIn(request.name, body)

    def test_each_request_gets_its_own_lead(self):
        first = self._make_request()
        second = self._make_request(subject="Autre besoin")
        self.assertNotEqual(first.lead_id, second.lead_id)

    def test_editing_a_request_does_not_duplicate_the_lead(self):
        request = self._make_request()
        lead = request.lead_id
        request.write({"subject": "Sujet revu"})
        self.assertEqual(request.lead_id, lead)
