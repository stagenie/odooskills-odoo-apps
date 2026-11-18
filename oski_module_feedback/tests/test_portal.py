"""Espace client : le demandeur suit ses demandes, et seulement les siennes."""
import json

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .common import feedback_vals, make_store_data


@tagged("post_install", "-at_install")
class TestFeedbackPortal(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        make_store_data(cls)
        Feedback = cls.env["oski.module.feedback"]
        cls.mine = Feedback.create(feedback_vals(cls, title="Mine one"))
        cls.mine2 = Feedback.create(feedback_vals(cls, title="Mine two"))
        cls.theirs = Feedback.create(feedback_vals(
            cls, title="Secret of Ben", partner_id=cls.other_user.partner_id.id))

    def setUp(self):
        super().setUp()
        self.authenticate("awa_fb", "awa_fb_12345")

    def test_home_counter(self):
        resp = self.url_open(
            "/my/counters", data=json.dumps({"params": {"counters": ["feedback_count"]}}),
            headers={"Content-Type": "application/json"})
        self.assertEqual(resp.json()["result"]["feedback_count"], 2)
        home = self.url_open("/my/home").text
        self.assertIn("/my/module-requests", home)

    def test_list_own_only(self):
        page = self.url_open("/my/module-requests").text
        self.assertIn(self.mine.name, page)
        self.assertIn(self.mine2.name, page)
        self.assertNotIn(self.theirs.name, page)

    def test_portal_foreign_request(self):
        resp = self.url_open("/my/module-requests/%s" % self.theirs.id, allow_redirects=False)
        self.assertNotEqual(resp.status_code, 200)
        self.assertNotIn("Secret of Ben", resp.text)

    def test_detail_shows_status_and_version(self):
        self.mine.write({"state": "done", "released_version": "19.0.1.2.0",
                         "decision_note": "Update the module to get it."})
        page = self.url_open("/my/module-requests/%s" % self.mine.id).text
        self.assertIn("Delivered", page)
        self.assertIn("19.0.1.2.0", page)
        self.assertIn("Update the module to get it.", page)
        self.assertIn("Mine one", page)
