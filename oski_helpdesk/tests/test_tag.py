from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger
from .common import HelpdeskCase


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestTag(HelpdeskCase):

    def test_tag_unique_name(self):
        self.env["helpdesk.tag"].create({"name": "ZzTestUnique"})
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self.env["helpdesk.tag"].create({"name": "ZzTestUnique"})

    def test_tag_create(self):
        tag = self.env["helpdesk.tag"].create({"name": "ZzTestColor", "color": 3})
        self.assertEqual(tag.color, 3)
