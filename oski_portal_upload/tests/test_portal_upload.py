import re
import unittest

from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged

CSRF = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


class PortalUploadCommon:
    """La suite s'appuie sur une fiche réellement visible au portail.

    ``portal.mixin`` est une classe abstraite : sans un modèle concret qui en
    hérite, rien de ce module ne peut être éprouvé de bout en bout. La tâche de
    projet est la fiche la plus légère à monter ; en son absence la suite
    s'abstient au lieu de mentir.
    """

    @classmethod
    def _skip_without_portal_model(cls):
        if "project.task" not in cls.env:
            raise unittest.SkipTest(
                "aucun modèle portail installé : le module project fournit la "
                "fiche d'essai de cette suite")

    @classmethod
    def _make_task(cls, name="Chantier"):
        project = cls.env["project.project"].create({"name": "Projet d'essai"})
        return cls.env["project.task"].create({
            "name": name, "project_id": project.id,
            "partner_id": cls.customer.id})


@tagged("post_install", "-at_install")
class TestPortalDocumentRequest(PortalUploadCommon, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._skip_without_portal_model()
        cls.customer = cls.env["res.partner"].create({
            "name": "Client Essai", "is_company": True})
        cls.contact = cls.env["res.partner"].create({
            "name": "Contact Essai", "parent_id": cls.customer.id})
        cls.stranger = cls.env["res.partner"].create({"name": "Tiers Essai"})
        cls.task = cls._make_task()
        cls.requests = cls.env["oski.portal.document.request"]

    def _request(self, **values):
        defaults = {
            "name": "Bon signé",
            "resource_ref": "%s,%s" % (self.task._name, self.task.id),
            "partner_id": self.customer.id,
        }
        defaults.update(values)
        return self.requests.create(defaults)

    def test_only_models_with_a_portal_page_can_be_targeted(self):
        offered = dict(self.requests._selection_target_model())
        self.assertIn("project.task", offered)
        self.assertNotIn("res.partner", offered,
                         "un contact n'a pas de page portail à héberger")

    def test_the_target_is_stored_apart_for_searching(self):
        document_request = self._request()
        self.assertEqual(document_request.res_model, "project.task")
        self.assertEqual(document_request.res_id, self.task.id)

    def test_the_customer_is_proposed_from_the_record(self):
        form = self.env["oski.portal.document.request"].new({
            "name": "Bon signé",
            "resource_ref": "%s,%s" % (self.task._name, self.task.id)})
        form._onchange_resource_ref()
        self.assertEqual(form.partner_id, self.customer)

    def test_a_pending_request_is_offered_to_the_customer(self):
        document_request = self._request()
        self.assertEqual(
            self.requests._oski_pending_for(self.task, self.customer),
            document_request)

    def test_another_contact_of_the_same_company_may_deposit(self):
        """Ce n'est pas toujours la personne nommée qui dépose le fichier."""
        document_request = self._request()
        self.assertEqual(
            self.requests._oski_pending_for(self.task, self.contact),
            document_request)

    def test_a_stranger_is_offered_nothing(self):
        self._request()
        self.assertFalse(
            self.requests._oski_pending_for(self.task, self.stranger))

    def test_a_request_of_another_record_is_not_offered(self):
        other_task = self._make_task("Autre chantier")
        self._request()
        self.assertFalse(
            self.requests._oski_pending_for(other_task, self.customer))

    def test_a_received_request_is_no_longer_offered(self):
        document_request = self._request()
        attachment = self.env["ir.attachment"].create({
            "name": "bon.pdf", "raw": b"contenu",
            "res_model": self.task._name, "res_id": self.task.id})
        document_request._oski_receive(attachment)
        self.assertEqual(document_request.state, "received")
        self.assertEqual(document_request.attachment_id, attachment)
        self.assertTrue(document_request.received_on)
        self.assertFalse(
            self.requests._oski_pending_for(self.task, self.customer))

    def test_the_deposit_is_told_on_the_record(self):
        """La trace part là où l'équipe regarde : le fil de la fiche."""
        document_request = self._request()
        before = len(self.task.message_ids)
        attachment = self.env["ir.attachment"].create({
            "name": "bon.pdf", "raw": b"contenu",
            "res_model": self.task._name, "res_id": self.task.id})
        document_request._oski_receive(attachment)
        self.assertEqual(len(self.task.message_ids), before + 1)
        message = self.task.message_ids[0]
        self.assertIn("bon.pdf", message.body)
        self.assertEqual(message.attachment_ids, attachment)

    def test_a_received_request_cannot_be_reopened(self):
        document_request = self._request()
        attachment = self.env["ir.attachment"].create({
            "name": "bon.pdf", "raw": b"contenu",
            "res_model": self.task._name, "res_id": self.task.id})
        document_request._oski_receive(attachment)
        with self.assertRaises(UserError):
            document_request.action_reset()

    def test_a_cancelled_request_can_be_asked_again(self):
        document_request = self._request()
        document_request.action_cancel()
        self.assertEqual(document_request.state, "cancelled")
        self.assertFalse(
            self.requests._oski_pending_for(self.task, self.customer))
        document_request.action_reset()
        self.assertEqual(document_request.state, "pending")

    def test_the_record_itself_answers_what_is_expected(self):
        """La fiche répond à partir de SON client, quel que soit l'utilisateur
        qui l'interroge : le portail sert ses pages en ``sudo``, l'identité du
        visiteur n'y est pas lisible."""
        document_request = self._request()
        employee = self.env["res.users"].create({
            "name": "Employé", "login": "oski_portal_employe",
            "partner_id": self.contact.id,
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.assertEqual(
            self.task.with_user(employee)._oski_document_requests(),
            document_request)
        self.assertEqual(
            self.task.with_user(self.env.ref("base.public_user")).sudo()
            ._oski_document_requests(),
            document_request)

    def test_a_request_for_another_customer_stays_off_the_page(self):
        self._request(partner_id=self.stranger.id)
        self.assertFalse(self.task._oski_document_requests())

    def test_the_settings_fall_back_on_readable_values(self):
        parameters = self.env["ir.config_parameter"].sudo()
        self.assertIn("pdf", self.requests._oski_allowed_extensions())
        parameters.set_param("oski_portal_upload.allowed_extensions", " PDF , .ZIP ")
        self.assertEqual(self.requests._oski_allowed_extensions(), ["pdf", "zip"])
        parameters.set_param("oski_portal_upload.max_size_mb", "un peu")
        self.assertEqual(self.requests._oski_max_size(), 15 * 1024 * 1024)
        parameters.set_param("oski_portal_upload.max_size_mb", "3")
        self.assertEqual(self.requests._oski_max_size(), 3 * 1024 * 1024)


@tagged("post_install", "-at_install")
class TestPortalUploadRoute(PortalUploadCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._skip_without_portal_model()
        cls.customer = cls.env["res.partner"].create({
            "name": "Client Portail", "email": "client.portail@example.com"})
        cls.portal_user = cls.env["res.users"].create({
            "name": "Client Portail", "login": "oski_portal_client",
            "password": "oski_portal_client",
            "partner_id": cls.customer.id,
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])]})
        cls.task = cls._make_task()
        cls.task._portal_ensure_token()

    def _page(self):
        return self.url_open("%s?access_token=%s" % (
            self.task.access_url, self.task.access_token))

    def _csrf(self, page):
        found = CSRF.search(page.text)
        self.assertTrue(found, "la page portail ne porte aucun jeton anti-rejeu")
        return found.group(1)

    def _upload(self, document_request, filename, content=b"contenu", csrf=None):
        page = self._page()
        token = csrf or self._csrf(page)
        return self.url_open(
            "/oski/portal/document/%s/upload" % document_request.id,
            data={"csrf_token": token, "access_token": self.task.access_token},
            files={"ufile": (filename, content)})

    def _request(self, **values):
        return self.env["oski.portal.document.request"].create(dict({
            "name": "Bon signé",
            "resource_ref": "%s,%s" % (self.task._name, self.task.id),
            "partner_id": self.customer.id,
        }, **values))

    def test_a_visitor_holding_the_link_also_sees_the_request(self):
        """Sans compte, muni du seul lien : c'est le cas qui compte le plus,
        et celui où la fiche est servie en ``sudo``."""
        self._request()
        page = self._page()
        self.assertEqual(page.status_code, 200)
        self.assertIn("Documents attendus", page.text)

    def test_the_page_shows_what_is_expected(self):
        self._request(note="Le bon signé et daté.")
        self.authenticate("oski_portal_client", "oski_portal_client")
        page = self._page()
        self.assertEqual(page.status_code, 200)
        self.assertIn("Documents attendus", page.text)
        self.assertIn("Bon signé", page.text)
        self.assertIn("Le bon signé et daté.", page.text)

    def test_the_page_stays_bare_when_nothing_is_expected(self):
        self.authenticate("oski_portal_client", "oski_portal_client")
        page = self._page()
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("Documents attendus", page.text)

    def test_the_customer_deposits_the_document(self):
        document_request = self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        response = self._upload(document_request, "bon.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertIn("oski_upload=ok", response.url)
        document_request.invalidate_recordset()
        self.assertEqual(document_request.state, "received")
        self.assertEqual(document_request.attachment_id.name, "bon.pdf")
        self.assertEqual(document_request.attachment_id.res_id, self.task.id)

    def test_a_refused_extension_sends_the_customer_back_with_the_reason(self):
        document_request = self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        response = self._upload(document_request, "virus.exe")
        self.assertIn("oski_upload=extension", response.url)
        document_request.invalidate_recordset()
        self.assertEqual(document_request.state, "pending")
        self.assertIn("n'est pas accepté", response.text)

    def test_a_file_beyond_the_limit_is_sent_back(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_portal_upload.max_size_mb", "1")
        document_request = self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        response = self._upload(document_request, "gros.pdf", b"x" * (2 * 1024 * 1024))
        self.assertIn("oski_upload=size", response.url)
        document_request.invalidate_recordset()
        self.assertEqual(document_request.state, "pending")

    def test_the_same_request_cannot_be_honoured_twice(self):
        document_request = self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        # Le jeton anti-rejeu est celui de la session, pas celui de la page :
        # après le premier dépôt la demande quitte l'écran, et c'est justement
        # ce second envoi hors écran qu'il faut éprouver.
        csrf = self._csrf(self._page())
        self._upload(document_request, "bon.pdf", csrf=csrf)
        response = self._upload(document_request, "encore.pdf", csrf=csrf)
        self.assertIn("oski_upload=closed", response.url)
        document_request.invalidate_recordset()
        self.assertEqual(document_request.attachment_id.name, "bon.pdf")

    def test_a_visitor_without_the_token_is_turned_away(self):
        """Le dépôt s'autorise sur la fiche, jamais sur la demande : sans
        droit de lecture ni jeton valide, rien ne se dépose."""
        document_request = self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        page = self._page()
        csrf = self._csrf(page)
        response = self.url_open(
            "/oski/portal/document/%s/upload" % document_request.id,
            data={"csrf_token": csrf, "access_token": "un-mauvais-jeton"},
            files={"ufile": ("bon.pdf", b"contenu")})
        self.assertEqual(response.status_code, 403)
        document_request.invalidate_recordset()
        self.assertEqual(document_request.state, "pending")

    def test_an_unknown_request_is_a_dead_end(self):
        self._request()
        self.authenticate("oski_portal_client", "oski_portal_client")
        page = self._page()
        csrf = self._csrf(page)
        response = self.url_open(
            "/oski/portal/document/999999/upload",
            data={"csrf_token": csrf, "access_token": self.task.access_token},
            files={"ufile": ("bon.pdf", b"contenu")})
        self.assertEqual(response.status_code, 404)
