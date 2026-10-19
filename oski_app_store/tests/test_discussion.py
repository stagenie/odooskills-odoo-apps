"""Discussion en bas de fiche : chatter portail, réservé aux utilisateurs connectés.

Un visiteur public voit une invitation à se connecter ; un utilisateur portail
voit le fil et peut y poster un commentaire sans droit d'écriture sur la fiche.
"""
import base64

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDiscussion(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        v19 = cls.env["oski.odoo.version"].search([("name", "=", "19.0")])
        att = cls.env["ir.attachment"].create(
            {"name": "d.zip", "datas": base64.b64encode(b"zip"), "public": True}
        )
        cls.module = cls.env["oski.module"].create(
            {
                "name": "Discussion Test Module",
                "technical_name": "oski_discussion_test",
                "is_published": True,
                "version_line_ids": [
                    (0, 0, {
                        "odoo_version_id": v19.id,
                        "module_version": "19.0.1.0.0",
                        "attachment_id": att.id,
                    })
                ],
            }
        )
        cls.portal_user = cls.env["res.users"].create({
            "name": "Portal Talker",
            "login": "oski_portal_talker",
            "password": "oski_portal_talker",
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })

    def test_module_is_a_thread_open_to_readers(self):
        Module = self.env["oski.module"]
        self.assertIn("mail.thread", Module._inherit)
        self.assertEqual(Module._mail_post_access, "read")

    def test_public_gets_sign_in_invitation_not_chatter(self):
        self.authenticate(None, None)
        html = self.url_open(self.module.website_url).text
        self.assertIn("oski-discussion", html)
        self.assertNotIn("o_portal_chatter", html)
        self.assertIn("/web/login?redirect=", html)

    def test_logged_in_user_gets_chatter(self):
        self.authenticate("oski_portal_talker", "oski_portal_talker")
        html = self.url_open(self.module.website_url).text
        self.assertIn("oski-discussion", html)
        self.assertIn("o_portal_chatter", html)
        self.assertIn('data-res_model="oski.module"', html)
        self.assertIn('data-res_id="%s"' % self.module.id, html)
        self.assertNotIn("/web/login?redirect=", html)

    def test_portal_user_can_post_a_comment(self):
        self.authenticate("oski_portal_talker", "oski_portal_talker")
        before = self.module.message_ids
        result = self.make_jsonrpc_request(
            "/mail/message/post",
            {
                "thread_model": "oski.module",
                "thread_id": self.module.id,
                "post_data": {
                    "body": "Works great on 19.0, thanks!",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                },
            },
        )
        self.assertTrue(result.get("message_id"))
        new = self.module.message_ids - before
        self.assertEqual(len(new), 1)
        self.assertEqual(new.author_id, self.portal_user.partner_id)
        self.assertEqual(new.message_type, "comment")
        self.assertIn("Works great", new.body)
        # Le commentaire fait partie du fil public de la fiche.
        self.assertIn(new, self.module.website_message_ids)

    def test_internal_note_stays_out_of_public_thread(self):
        note = self.module.message_post(body="internal note", message_type="notification")
        self.assertNotIn(note, self.module.website_message_ids)
