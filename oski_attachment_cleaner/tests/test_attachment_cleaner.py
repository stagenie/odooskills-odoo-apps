import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

CONTENT = base64.b64encode(b"contenu de recette")
OTHER = base64.b64encode(b"un autre contenu")


@tagged("post_install", "-at_install")
class TestAttachmentCleaner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attachment = cls.env["ir.attachment"]
        cls.partner = cls.env["res.partner"].create({"name": "Client vivant"})

    def _attachment(self, age_days=90, **vals):
        values = {
            "name": vals.pop("name", "piece.txt"),
            "datas": vals.pop("datas", CONTENT),
        }
        values.update(vals)
        attachment = self.Attachment.create(values)
        born = fields.Datetime.now() - timedelta(days=age_days)
        self.env.cr.execute(
            "UPDATE ir_attachment SET create_date = %s WHERE id = %s", (born, attachment.id))
        attachment.invalidate_recordset(["create_date"])
        return attachment

    def _delete_in_db(self, record):
        """Supprime l'enregistrement **sans** passer par l'ORM.

        C'est ainsi que naissent les vraies orphelines : ``unlink()`` d'Odoo
        emporte les pièces jointes du document au passage, donc une suppression
        ordinaire n'en laisse aucune. Restent les suppressions en cascade au
        niveau de la base, les migrations et les scripts SQL — d'où ce module.
        """
        table = record._table
        self.env.cr.execute("DELETE FROM %s WHERE id = %%s" % table, (record.id,))
        record.invalidate_recordset()

    def _cleaner(self, **vals):
        return self.env["oski.attachment.cleaner"].create(vals)

    # --- orphelines -------------------------------------------------------

    def test_an_orphan_is_found(self):
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(res_model="res.partner", res_id=doomed.id)
        self._delete_in_db(doomed)
        self.assertIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_live_record_keeps_its_attachment(self):
        attachment = self._attachment(res_model="res.partner", res_id=self.partner.id)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_an_archived_record_is_not_an_orphan(self):
        """Archiver n'est pas supprimer : la recherche désactive le filtre
        d'activité, sinon toute pièce d'un client archivé serait proposée."""
        self.partner.active = False
        attachment = self._attachment(res_model="res.partner", res_id=self.partner.id)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_field_value_is_never_touched(self):
        """``res_field`` renseigné : la pièce **est** la valeur du champ."""
        attachment = self._attachment(
            res_model="res.partner", res_id=self.partner.id, res_field="image_1920")
        self._delete_in_db(self.partner)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_served_file_is_never_touched(self):
        attachment = self._attachment(
            name="bundle.js", datas=False, url="/web/assets/1/bundle.js",
            res_model="res.partner", res_id=0)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_public_file_is_never_touched(self):
        attachment = self._attachment(
            res_model="res.partner", res_id=0, public=True)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_protected_model_is_never_touched(self):
        attachment = self._attachment(res_model="ir.ui.view", res_id=999999999)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_a_recent_attachment_is_never_touched(self):
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(age_days=1, res_model="res.partner", res_id=doomed.id)
        self._delete_in_db(doomed)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    def test_an_uninstalled_model_is_left_alone(self):
        """Le modèle a disparu avec son module : réinstaller le rendrait de
        nouveau utile, et une purge est sans retour."""
        attachment = self._attachment(res_model="x.module.parti", res_id=42)
        self.assertNotIn(attachment, self.Attachment._oski_find_orphans(30))

    # --- copies redondantes ----------------------------------------------

    def test_the_second_copy_of_the_same_document_is_redundant(self):
        first = self._attachment(res_model="res.partner", res_id=self.partner.id)
        second = self._attachment(res_model="res.partner", res_id=self.partner.id)
        duplicates = self.Attachment._oski_find_duplicates(30)
        self.assertIn(second, duplicates)
        self.assertNotIn(first, duplicates, "la plus ancienne est conservée")

    def test_the_same_file_on_two_documents_is_not_redundant(self):
        """Un contrat type ou un logo attaché à deux clients : supprimer l'une
        des deux copies priverait un document de sa pièce."""
        other = self.env["res.partner"].create({"name": "Autre client"})
        first = self._attachment(res_model="res.partner", res_id=self.partner.id)
        second = self._attachment(res_model="res.partner", res_id=other.id)
        duplicates = self.Attachment._oski_find_duplicates(30)
        self.assertNotIn(first, duplicates)
        self.assertNotIn(second, duplicates)

    def test_two_different_files_are_not_redundant(self):
        first = self._attachment(res_model="res.partner", res_id=self.partner.id)
        second = self._attachment(
            res_model="res.partner", res_id=self.partner.id, datas=OTHER)
        duplicates = self.Attachment._oski_find_duplicates(30)
        self.assertNotIn(first, duplicates)
        self.assertNotIn(second, duplicates)

    # --- relevé et purge --------------------------------------------------

    def test_the_scan_counts_without_deleting(self):
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(res_model="res.partner", res_id=doomed.id)
        self._delete_in_db(doomed)
        cleaner = self._cleaner()
        cleaner.action_scan()
        self.assertTrue(cleaner.scanned)
        self.assertEqual(cleaner.candidate_count, 1)
        self.assertIn(attachment.name, cleaner.candidate_preview)
        self.assertGreaterEqual(cleaner.candidate_bytes, attachment.file_size)
        self.assertTrue(attachment.exists(), "le relevé ne supprime rien")

    def test_nothing_is_purged_before_it_has_been_read(self):
        cleaner = self._cleaner()
        with self.assertRaises(UserError):
            cleaner.action_purge()

    def test_the_purge_deletes_and_leaves_a_trace(self):
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(res_model="res.partner", res_id=doomed.id)
        size = attachment.file_size
        self._delete_in_db(doomed)
        cleaner = self._cleaner(include_duplicates=False)
        cleaner.action_scan()
        cleaner.action_purge()
        self.assertFalse(attachment.exists())
        purge = self.env["oski.attachment.purge"].search([], limit=1)
        self.assertEqual(purge.attachment_count, 1)
        self.assertEqual(purge.freed_bytes, size)
        self.assertEqual(purge.user_id, self.env.user)
        self.assertIn("orphelines", purge.criteria)

    def test_the_purge_recomputes_and_never_trusts_the_scan(self):
        """Entre le relevé et la purge, la base a continué de vivre."""
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(res_model="res.partner", res_id=doomed.id)
        self._delete_in_db(doomed)
        cleaner = self._cleaner(include_duplicates=False)
        cleaner.action_scan()
        attachment.unlink()
        with self.assertRaises(UserError):
            cleaner.action_purge()

    def test_a_live_attachment_survives_a_purge(self):
        kept = self._attachment(res_model="res.partner", res_id=self.partner.id)
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        orphan = self._attachment(res_model="res.partner", res_id=doomed.id, datas=OTHER)
        self._delete_in_db(doomed)
        cleaner = self._cleaner()
        cleaner.action_scan()
        cleaner.action_purge()
        self.assertTrue(kept.exists())
        self.assertFalse(orphan.exists())

    def test_the_tool_is_closed_to_ordinary_users(self):
        """``TransactionCase.env`` est superutilisateur : sans ``with_user``,
        aucun droit n'est éprouvé."""
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_att_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        with self.assertRaises(AccessError):
            self.env["oski.attachment.cleaner"].with_user(user).create({})

    def test_an_administrator_who_is_not_the_superuser_sees_the_orphans(self):
        """Le scénario qui compte, et le seul que ``TransactionCase`` masque.

        ``ir.attachment`` fait dépendre l'accès à une pièce de l'accès à son
        document : une orpheline n'ayant plus de document, un administrateur
        ordinaire ne la voit pas. Sans ce test joué ``with_user``, l'outil
        semble marcher et ne trouve jamais rien en production.
        """
        admin = self.env["res.users"].create({
            "name": "Administratrice", "login": "oski_att_admin",
            "group_ids": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("base.group_system").id])]})
        doomed = self.env["res.partner"].create({"name": "Client supprimé"})
        attachment = self._attachment(res_model="res.partner", res_id=doomed.id)
        self._delete_in_db(doomed)
        cleaner = self.env["oski.attachment.cleaner"].with_user(admin).create(
            {"include_duplicates": False})
        cleaner.action_scan()
        self.assertEqual(cleaner.candidate_count, 1)
        self.assertIn(attachment.name, cleaner.candidate_preview)
        cleaner.action_purge()
        self.assertFalse(attachment.exists())
