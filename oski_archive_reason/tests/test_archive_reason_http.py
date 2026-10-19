import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestArchiveReasonHttp(HttpCase):

    def test_web_client_archive_returns_wizard(self):
        """Le bouton « Archiver » (route call_kw du client web) ouvre l'assistant."""
        partner = self.env["res.partner"].create({"name": "Archivage par l'interface"})
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/web/dataset/call_kw/res.partner/action_archive",
            data=json.dumps({
                "jsonrpc": "2.0", "method": "call", "id": 1,
                "params": {"model": "res.partner", "method": "action_archive",
                           "args": [partner.ids], "kwargs": {}},
            }),
            headers={"Content-Type": "application/json"},
        )
        result = response.json().get("result")
        self.assertIsInstance(result, dict, response.text[:300])
        self.assertEqual(result.get("res_model"), "oski.archive.reason.wizard")
        partner.invalidate_recordset(["active"])
        self.assertTrue(partner.active, "Sans motif, le contact reste actif.")
