from odoo.tests import tagged
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestTag(HelpdeskCase):

    def test_tag_unique_name(self):
        self.env["helpdesk.tag"].create({"name": "Bug"})
        with self.assertRaises(Exception):
            self.env["helpdesk.tag"].create({"name": "Bug"})

    def test_tag_create(self):
        tag = self.env["helpdesk.tag"].create({"name": "Question", "color": 3})
        self.assertEqual(tag.color, 3)
