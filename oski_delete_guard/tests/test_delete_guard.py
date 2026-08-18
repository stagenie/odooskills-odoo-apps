from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestDeleteGuard(TransactionCase):
    """Le garde-fou ne s'applique qu'aux utilisateurs réels.

    ``TransactionCase.env`` tourne en superutilisateur : toute suppression
    lancée depuis ``self.env`` traverse le garde-fou sans être vue, exactement
    comme une installation ou une tâche planifiée. Les scénarios utilisateur
    passent donc tous par ``with_user``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.Rule = cls.env["oski.delete.rule"]
        cls.Log = cls.env["oski.delete.log"]
        cls.user = cls._make_user(cls, "supprimeur@example.com")

    def _make_user(self, login, groups=None):
        base_groups = [
            self.env.ref("base.group_user").id,
            # Sans ce groupe, l'ORM refuse la suppression d'un contact avant
            # même que le garde-fou soit consulté.
            self.env.ref("base.group_partner_manager").id,
        ]
        return self.env["res.users"].create({
            "name": login, "login": login,
            "group_ids": [(6, 0, base_groups + (groups or []))],
        })

    def _rule(self, **vals):
        return self.Rule.create(dict(model_id=self.partner_model.id, **vals))

    def _partner(self, name):
        return self.Partner.create({"name": name})

    # ------------------------------------------------------------------
    # Sans règle, rien ne change
    # ------------------------------------------------------------------

    def test_unwatched_model_deletes_freely_and_silently(self):
        partner = self._partner("Libre")
        partner.with_user(self.user).unlink()
        self.assertFalse(partner.exists())
        self.assertFalse(self.Log.search([("model_name", "=", "res.partner")]))

    # ------------------------------------------------------------------
    # Mode « interdire »
    # ------------------------------------------------------------------

    def test_block_refuses_deletion(self):
        self._rule(mode="block")
        partner = self._partner("Protégé")
        with self.assertRaises(UserError):
            partner.with_user(self.user).unlink()
        self.assertTrue(partner.exists(), "L'enregistrement doit survivre au refus.")

    def test_block_uses_the_custom_message(self):
        self._rule(mode="block", message="Archivez plutôt que de supprimer.")
        partner = self._partner("Protégé")
        with self.assertRaisesRegex(UserError, "Archivez plutôt"):
            partner.with_user(self.user).unlink()

    def test_allowed_group_still_deletes_and_leaves_a_trace(self):
        group = self.env["res.groups"].create({"name": "Fossoyeurs"})
        self._rule(mode="block", group_ids=[(6, 0, group.ids)])
        user = self._make_user("autorise@example.com", groups=group.ids)
        partner = self._partner("Sacrifié")
        partner_id = partner.id
        partner.with_user(user).unlink()
        self.assertFalse(partner.exists())
        log = self.Log.search([("res_id", "=", partner_id), ("model_name", "=", "res.partner")])
        self.assertEqual(len(log), 1, "L'exception doit laisser une trace.")
        self.assertEqual(log.user_id, user)
        self.assertEqual(log.res_name, "Sacrifié")

    def test_block_without_group_stops_the_administrator_too(self):
        self._rule(mode="block")
        admin = self._make_user("admin.faux@example.com",
                                groups=[self.env.ref("base.group_system").id])
        partner = self._partner("Intouchable")
        with self.assertRaises(UserError):
            partner.with_user(admin).unlink()

    # ------------------------------------------------------------------
    # Mode « journaliser »
    # ------------------------------------------------------------------

    def test_log_mode_lets_deletion_through(self):
        self._rule(mode="log")
        partner = self._partner("Tracé")
        partner_id = partner.id
        partner.with_user(self.user).unlink()
        self.assertFalse(partner.exists())
        log = self.Log.search([("res_id", "=", partner_id), ("model_name", "=", "res.partner")])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.res_name, "Tracé")
        self.assertEqual(log.model_label, self.partner_model.name)
        self.assertEqual(log.user_id, self.user)

    def test_log_records_every_line_of_a_batch(self):
        self._rule(mode="log")
        partners = self.Partner.create([{"name": "A1"}, {"name": "A2"}, {"name": "A3"}])
        ids = partners.ids
        partners.with_user(self.user).unlink()
        logs = self.Log.search([("res_id", "in", ids), ("model_name", "=", "res.partner")])
        self.assertEqual(len(logs), 3, "Une ligne de journal par enregistrement.")

    # ------------------------------------------------------------------
    # Le cache suit les règles
    # ------------------------------------------------------------------

    def test_rule_change_takes_effect_immediately(self):
        rule = self._rule(mode="block")
        partner = self._partner("Bascule")
        with self.assertRaises(UserError):
            partner.with_user(self.user).unlink()
        rule.mode = "log"
        partner.with_user(self.user).unlink()
        self.assertFalse(partner.exists(), "Le cache de règles doit suivre la modification.")

    def test_deleting_the_rule_reopens_the_model(self):
        self._rule(mode="block").unlink()
        partner = self._partner("Libéré")
        partner.with_user(self.user).unlink()
        self.assertFalse(partner.exists())

    # ------------------------------------------------------------------
    # Maintenance et journal lui-même
    # ------------------------------------------------------------------

    def test_superuser_is_never_blocked(self):
        self._rule(mode="block")
        partner = self._partner("Maintenance")
        partner.sudo().unlink()
        self.assertFalse(partner.exists(), "Une opération système ne doit jamais être arrêtée.")

    def test_purging_the_log_does_not_feed_it(self):
        self._rule(mode="log")
        partner = self._partner("Éphémère")
        partner.with_user(self.user).unlink()
        logs = self.Log.search([("model_name", "=", "res.partner")])
        self.assertTrue(logs)
        logs.unlink()
        self.assertFalse(
            self.Log.search([("model_name", "=", "oski.delete.log")]),
            "Purger le journal ne doit pas écrire dans le journal.",
        )
