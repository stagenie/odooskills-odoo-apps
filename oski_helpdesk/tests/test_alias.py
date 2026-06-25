from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestAlias(HelpdeskCase):

    def test_message_new_creates_ticket(self):
        team = self.env["helpdesk.team"].create({"name": "Mail"})
        msg = {
            "subject": "Imprimante en panne",
            "email_from": "client@example.com",
            "body": "<p>Plus de toner</p>",
            "to": "support@example.com",
        }
        ticket = self.env["helpdesk.ticket"].with_context(
            default_team_id=team.id).message_new(msg, {"team_id": team.id})
        self.assertEqual(ticket.name, "Imprimante en panne")
        self.assertEqual(ticket.partner_email, "client@example.com")
        self.assertTrue(ticket.number.startswith("HT/"))
