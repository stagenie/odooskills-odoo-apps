from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.oski_app_store.controllers.url_state import build_query, toggle


@tagged("post_install", "-at_install")
class TestUrlState(TransactionCase):
    def test_toggle_adds_absent(self):
        self.assertEqual(toggle([1, 2], 3), [1, 2, 3])

    def test_toggle_removes_present(self):
        self.assertEqual(toggle([1, 2, 3], 2), [1, 3])

    def test_build_query_empty(self):
        self.assertEqual(
            build_query([], [], "all", "name", "", "19.0"), "/apps"
        )

    def test_build_query_multi_tags(self):
        url = build_query([], [1, 2], "all", "name", "", "19.0")
        self.assertEqual(url, "/apps?tag=1&tag=2")

    def test_build_query_encodes_search(self):
        url = build_query([], [], "all", "name", "a & b", "19.0")
        self.assertIn("search=a+%26+b", url)

    def test_build_query_omits_defaults(self):
        url = build_query([5], [], "all", "name", "", "19.0")
        self.assertEqual(url, "/apps?category=5")

    def test_build_query_keeps_non_defaults(self):
        url = build_query([], [], "free", "recent", "", "18.0", "19.0")
        self.assertIn("pricing=free", url)
        self.assertIn("sort=recent", url)
        self.assertIn("v=18.0", url)
