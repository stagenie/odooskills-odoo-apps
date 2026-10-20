from odoo.exceptions import AccessError
from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestAccess(HelpdeskCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g_user = cls.env.ref("oski_helpdesk.group_helpdesk_user")
        cls.g_mgr = cls.env.ref("oski_helpdesk.group_helpdesk_manager")

    def test_user_cannot_create_team(self):
        user = self._make_user("hd_plain", [self.g_user])
        with self.assertRaises(AccessError):
            self.env["helpdesk.team"].with_user(user).create({"name": "X"})

    def test_user_can_create_ticket(self):
        user = self._make_user("hd_plain2", [self.g_user])
        team = self.env["helpdesk.team"].create({"name": "T"})
        ticket = self.env["helpdesk.ticket"].with_user(user).create({
            "name": "Souci", "team_id": team.id})
        self.assertTrue(ticket.number.startswith("HT/"))

    def test_manager_can_create_team(self):
        mgr = self._make_user("hd_mgr", [self.g_mgr])
        team = self.env["helpdesk.team"].with_user(mgr).create({"name": "Y"})
        self.assertTrue(team.id)

    def test_multi_company_isolation(self):
        """Un agent d'une société ne voit ni les équipes ni les tickets d'une
        autre société."""
        other = self.env["res.company"].create({"name": "Autre société HD"})
        team_o = self.env["helpdesk.team"].create({"name": "TO", "company_id": other.id})
        ticket_o = self.env["helpdesk.ticket"].create({
            "name": "Ailleurs", "team_id": team_o.id, "company_id": other.id})
        user = self._make_user("hd_mc", [self.g_user])
        self.assertFalse(self.env["helpdesk.ticket"].with_user(user).search(
            [("id", "=", ticket_o.id)]))
        self.assertFalse(self.env["helpdesk.team"].with_user(user).search(
            [("id", "=", team_o.id)]))
        with self.assertRaises(AccessError):
            ticket_o.with_user(user).read(["name"])
