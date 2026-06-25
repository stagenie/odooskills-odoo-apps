from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestAssignment(HelpdeskCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.u1 = cls.env["res.users"].create({"name": "hd_a", "login": "hd_a"})
        cls.u2 = cls.env["res.users"].create({"name": "hd_b", "login": "hd_b"})
        cls.team_bal = cls.env["helpdesk.team"].create({
            "name": "Bal", "assignment_method": "balanced",
            "member_ids": [(6, 0, [cls.u1.id, cls.u2.id])]})
        cls.team_man = cls.env["helpdesk.team"].create({
            "name": "Man", "assignment_method": "manual",
            "member_ids": [(6, 0, [cls.u1.id, cls.u2.id])]})

    def test_balanced_picks_least_loaded(self):
        # u1 a déjà 1 ticket ouvert
        self.env["helpdesk.ticket"].create({
            "name": "pre", "team_id": self.team_bal.id, "user_id": self.u1.id})
        t = self.env["helpdesk.ticket"].create({
            "name": "auto", "team_id": self.team_bal.id})
        self.assertEqual(t.user_id, self.u2)

    def test_balanced_skip_if_user_set(self):
        t = self.env["helpdesk.ticket"].create({
            "name": "fix", "team_id": self.team_bal.id, "user_id": self.u1.id})
        self.assertEqual(t.user_id, self.u1)

    def test_manual_no_autoassign(self):
        t = self.env["helpdesk.ticket"].create({
            "name": "m", "team_id": self.team_man.id})
        self.assertFalse(t.user_id)
