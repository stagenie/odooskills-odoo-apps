from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestTicket(HelpdeskCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["helpdesk.team"].create({"name": "Support"})

    def test_sequence_number(self):
        t1 = self.env["helpdesk.ticket"].create({"name": "Souci A", "team_id": self.team.id})
        t2 = self.env["helpdesk.ticket"].create({"name": "Souci B", "team_id": self.team.id})
        self.assertTrue(t1.number.startswith("HT/"))
        self.assertNotEqual(t1.number, t2.number)

    def test_default_stage(self):
        t = self.env["helpdesk.ticket"].create({"name": "X", "team_id": self.team.id})
        first = self.env["helpdesk.stage"].search([], order="sequence, id", limit=1)
        self.assertEqual(t.stage_id, first)

    def test_team_ticket_count(self):
        team = self.env["helpdesk.team"].create({"name": "CountTeam"})
        self.env["helpdesk.ticket"].create({"name": "C1", "team_id": team.id})
        self.env["helpdesk.ticket"].create({"name": "C2", "team_id": team.id})
        self.assertEqual(team.ticket_count, 2)
