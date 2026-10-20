from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestStage(HelpdeskCase):

    def test_stages_ordered(self):
        stages = self.env["helpdesk.stage"].search([])
        seqs = stages.mapped("sequence")
        self.assertEqual(seqs, sorted(seqs))

    def test_close_stage_exists(self):
        closed = self.env["helpdesk.stage"].search([("is_close", "=", True)])
        self.assertTrue(closed, "Au moins une étape terminale attendue (data)")
