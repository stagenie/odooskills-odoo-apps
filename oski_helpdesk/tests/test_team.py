from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestTeam(HelpdeskCase):

    def test_team_defaults(self):
        team = self.env["helpdesk.team"].create({"name": "Support"})
        self.assertEqual(team.assignment_method, "manual")

    def test_team_members(self):
        u = self._make_user("hd_member")
        team = self.env["helpdesk.team"].create({
            "name": "IT", "member_ids": [(6, 0, u.ids)]})
        self.assertIn(u, team.member_ids)
