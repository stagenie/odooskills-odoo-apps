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
