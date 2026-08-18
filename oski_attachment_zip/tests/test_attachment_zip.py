import base64
import io
import zipfile

from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, tagged

CONTENT = base64.b64encode(b"contenu")


class ZipCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.first = cls.env["res.partner"].create({"name": "Fiche Une"})
        cls.second = cls.env["res.partner"].create({"name": "Fiche Deux"})
        cls.attachments = cls.env["ir.attachment"]

    def _attach(self, record, name, datas=CONTENT, **values):
        attachment = self.env["ir.attachment"].create(dict({
            "name": name,
            "datas": datas,
            "res_model": record._name,
            "res_id": record.id,
        }, **values))
        return attachment

    def _entries(self, records):
        _name, content = self.env["ir.attachment"]._oski_zip_bytes(records)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return archive.namelist()


@tagged("post_install", "-at_install")
class TestZipActivation(ZipCommon):
    """La case cochée sur le modèle est le seul interrupteur ; l'action
    contextuelle qu'elle pose doit suivre exactement."""

    def test_ticking_the_box_posts_the_menu_entry(self):
        self.partner_model.oski_zip_enabled = True
        action = self.partner_model.oski_zip_action_id
        self.assertTrue(action)
        self.assertEqual(action.binding_model_id, self.partner_model)
        self.assertEqual(action.binding_type, "action")
        self.assertEqual(action.binding_view_types, "list,form")
        self.assertEqual(action.state, "code")

    def test_unticking_it_removes_the_entry(self):
        self.partner_model.oski_zip_enabled = True
        action = self.partner_model.oski_zip_action_id
        self.partner_model.oski_zip_enabled = False
        self.assertFalse(action.exists())
        self.assertFalse(self.partner_model.oski_zip_action_id)

    def test_ticking_twice_posts_a_single_entry(self):
        self.partner_model.oski_zip_enabled = True
        action = self.partner_model.oski_zip_action_id
        self.partner_model.write({"oski_zip_enabled": True})
        self.assertEqual(self.partner_model.oski_zip_action_id, action)
        self.assertEqual(self.env["ir.actions.server"].search_count([
            ("binding_model_id", "=", self.partner_model.id),
            ("name", "like", "ZIP"),
        ]), 1)

    def test_an_entry_deleted_by_hand_comes_back(self):
        self.partner_model.oski_zip_enabled = True
        self.partner_model.oski_zip_action_id.unlink()
        self.assertFalse(self.partner_model.oski_zip_action_id)
        self.partner_model.oski_zip_enabled = False
        self.partner_model.oski_zip_enabled = True
        self.assertTrue(self.partner_model.oski_zip_action_id)

    def test_a_transient_model_gets_nothing(self):
        wizard_model = self.env["ir.model"]._get("base.language.install")
        self.assertFalse(wizard_model.oski_zip_available)
        wizard_model.oski_zip_enabled = True
        self.assertFalse(wizard_model.oski_zip_action_id)

    def test_an_abstract_model_gets_nothing(self):
        """Un mixin n'a pas de fiche : lui poser une entrée de menu
        promettrait un écran qui n'existe pas."""
        mixin = self.env["ir.model"]._get("mail.thread")
        self.assertFalse(mixin.oski_zip_available)
        mixin.oski_zip_enabled = True
        self.assertFalse(mixin.oski_zip_action_id)

    def test_a_real_model_is_offered(self):
        self.assertTrue(self.partner_model.oski_zip_available)

    def test_the_configuration_screen_only_lists_real_models(self):
        offered = self.env["ir.model"].search([("oski_zip_available", "=", True)])
        self.assertIn(self.partner_model, offered)
        self.assertNotIn(self.env["ir.model"]._get("mail.thread"), offered)
        hidden = self.env["ir.model"].search([("oski_zip_available", "=", False)])
        self.assertIn(self.env["ir.model"]._get("mail.thread"), hidden)
        self.assertNotIn(self.partner_model, hidden)


@tagged("post_install", "-at_install")
class TestZipContent(ZipCommon):

    def test_the_action_hands_back_a_download_url(self):
        self._attach(self.first, "devis.pdf")
        action = self.env["ir.attachment"]._oski_zip_action(self.first)
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "download")
        self.assertIn("model=res.partner", action["url"])
        self.assertIn("ids=%s" % self.first.id, action["url"])

    def test_a_selection_without_attachments_is_refused_up_front(self):
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._oski_zip_action(self.first)

    def test_an_empty_selection_is_refused(self):
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._oski_zip_action(self.env["res.partner"])

    def test_the_archive_holds_the_files_of_the_record(self):
        self._attach(self.first, "devis.pdf")
        self._attach(self.first, "plan.png")
        self._attach(self.second, "ailleurs.pdf")
        self.assertEqual(sorted(self._entries(self.first)),
                         ["devis.pdf", "plan.png"])

    def test_binary_field_values_are_not_attachments(self):
        """``res_field`` désigne la valeur d'un champ binaire — un logo, une
        photo — et non une pièce jointe déposée sur la fiche."""
        self._attach(self.first, "devis.pdf")
        self._attach(self.first, "image_1920", res_field="image_1920")
        self.assertEqual(self._entries(self.first), ["devis.pdf"])

    def test_a_file_served_by_url_has_no_content_to_archive(self):
        self._attach(self.first, "devis.pdf")
        self.env["ir.attachment"].create({
            "name": "lien.html", "url": "/quelque/part",
            "res_model": self.first._name, "res_id": self.first.id})
        self.assertEqual(self._entries(self.first), ["devis.pdf"])

    def test_two_files_of_the_same_name_stay_distinct(self):
        self._attach(self.first, "devis.pdf")
        self._attach(self.first, "devis.pdf")
        self.assertEqual(sorted(self._entries(self.first)),
                         ["devis (2).pdf", "devis.pdf"])

    def test_several_records_are_filed_in_folders(self):
        self._attach(self.first, "devis.pdf")
        self._attach(self.second, "devis.pdf")
        entries = sorted(self._entries(self.first | self.second))
        self.assertEqual(entries, ["Fiche Deux/devis.pdf", "Fiche Une/devis.pdf"])

    def test_a_file_name_never_becomes_a_path(self):
        """Une pièce nommée ``../../passwd`` écrirait hors de son dossier
        chez qui décompresse l'archive."""
        self._attach(self.first, "../../etc/passwd")
        self.assertEqual(self._entries(self.first), ["_.._etc_passwd"])

    def test_the_archive_name_says_what_it_holds(self):
        self._attach(self.first, "devis.pdf")
        name, _content = self.env["ir.attachment"]._oski_zip_bytes(self.first)
        self.assertIn("Fiche Une", name)
        self.assertTrue(name.endswith(".zip"))
        self._attach(self.second, "devis.pdf")
        name, _content = self.env["ir.attachment"]._oski_zip_bytes(
            self.first | self.second)
        self.assertIn("2 fiches", name)

    def test_too_many_records_are_refused(self):
        partners = self.env["res.partner"].create(
            [{"name": "Masse %s" % index} for index in range(201)])
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._oski_zip_action(partners)

    def test_an_archive_beyond_the_limit_is_refused(self):
        self._attach(self.first, "devis.pdf")
        parameters = self.env["ir.config_parameter"].sudo()
        parameters.set_param("oski_attachment_zip.max_size_mb", "0.000001")
        with self.assertRaises(UserError):
            self._entries(self.first)
        # Zéro lève la limite, et une valeur illisible retombe sur la valeur
        # par défaut : dans les deux cas le téléchargement aboutit.
        parameters.set_param("oski_attachment_zip.max_size_mb", "0")
        self.assertTrue(self._entries(self.first))
        parameters.set_param("oski_attachment_zip.max_size_mb", "plus tard")
        self.assertTrue(self._entries(self.first))

    def test_a_user_who_cannot_read_the_record_gets_nothing(self):
        """Les pièces se lisent avec les droits de l'appelant : le contrôle
        d'accès du document commande celui de ses fichiers."""
        server = self.env["ir.mail_server"].create({
            "name": "Serveur d'essai", "smtp_host": "localhost"})
        self._attach(server, "secret.pdf")
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_zip_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.assertFalse(user.has_group("base.group_system"))
        with self.assertRaises(AccessError):
            self.env["ir.attachment"].with_user(user)._oski_zip_bytes(
                server.with_user(user))


@tagged("post_install", "-at_install")
class TestZipRoute(HttpCase):

    def test_the_route_serves_the_archive(self):
        partner = self.env["res.partner"].create({"name": "Fiche Servie"})
        self.env["ir.attachment"].create({
            "name": "devis.pdf", "datas": CONTENT,
            "res_model": "res.partner", "res_id": partner.id})
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/oski/attachment/zip?model=res.partner&ids=%s" % partner.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ["devis.pdf"])

    def test_an_unknown_model_is_a_dead_end(self):
        self.authenticate("admin", "admin")
        response = self.url_open("/oski/attachment/zip?model=pas.un.modele&ids=1")
        self.assertEqual(response.status_code, 404)

    def test_a_record_without_attachments_is_a_dead_end(self):
        partner = self.env["res.partner"].create({"name": "Fiche Nue"})
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/oski/attachment/zip?model=res.partner&ids=%s" % partner.id)
        self.assertEqual(response.status_code, 404)
