from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import feedback_vals, make_store_data


@tagged("post_install", "-at_install")
class TestFeedbackModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_store_data(cls)
        cls.Feedback = cls.env["oski.module.feedback"]

    def test_reference_numbering(self):
        rec = self.Feedback.create(feedback_vals(self))
        self.assertTrue(rec.name.startswith("FB"))
        self.assertEqual(len(rec.name), 7)

    def test_requester_follows(self):
        rec = self.Feedback.create(feedback_vals(self))
        self.assertIn(self.portal_user.partner_id, rec.message_partner_ids)

    def test_done_requires_version(self):
        rec = self.Feedback.create(feedback_vals(self))
        with self.assertRaises(ValidationError):
            rec.write({"state": "done"})
        rec.write({"state": "done", "released_version": "19.0.1.2.0"})
        self.assertEqual(rec.state, "done")

    def test_max_per_day_default(self):
        param = self.env["ir.config_parameter"].sudo()
        param.set_param("oski_module_feedback.max_per_day", False)
        self.assertEqual(self.Feedback._max_per_day(), 5)
        param.set_param("oski_module_feedback.max_per_day", "0")
        self.assertEqual(self.Feedback._max_per_day(), 5)
        param.set_param("oski_module_feedback.max_per_day", "8")
        self.assertEqual(self.Feedback._max_per_day(), 8)

    def test_count_last_24h(self):
        partner = self.portal_user.partner_id
        self.Feedback.create(feedback_vals(self))
        self.Feedback.create(feedback_vals(self))
        old = self.Feedback.create(feedback_vals(self))
        self.env.cr.execute(
            "UPDATE oski_module_feedback SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=2), old.id),
        )
        self.assertEqual(self.Feedback._count_last_24h(partner), 2)

    def test_feedback_count(self):
        self.Feedback.create(feedback_vals(self))
        self.Feedback.create(feedback_vals(self))
        self.paid.invalidate_recordset(["feedback_count"])
        self.assertEqual(self.paid.feedback_count, 2)

    def test_access_url(self):
        rec = self.Feedback.create(feedback_vals(self))
        self.assertEqual(rec.access_url, "/my/module-requests/%s" % rec.id)
