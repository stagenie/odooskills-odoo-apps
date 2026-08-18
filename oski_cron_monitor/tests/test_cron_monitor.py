from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

CORE_CALLBACK = "odoo.addons.base.models.ir_cron.IrCron._callback"


@tagged("post_install", "-at_install")
class TestCronMonitor(TransactionCase):
    """Le journal s'écrit sur un curseur qui lui est propre, donc hors de la
    transaction du test : chaque scénario détourne ``_oski_run_env`` vers
    l'environnement du test, sinon les lignes seraient réellement commitées
    dans la base et invisibles depuis le test.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_partner = cls.env["ir.model"]._get("res.partner")
        cls.cron = cls.env["ir.cron"].create({
            "name": "Tâche de recette",
            "model_id": cls.model_partner.id,
            "state": "code",
            "code": "model.search([], limit=1)",
            "interval_number": 1,
            "interval_type": "days",
        })
        cls.Run = cls.env["oski.cron.run"]

    @contextmanager
    def _test_env(self):
        yield self.env

    def _patched_env(self):
        return patch.object(
            type(self.env["ir.cron"]), "_oski_run_env", lambda record: self._test_env())

    def _call(self, cron, failure=None):
        """Exécute la tâche en neutralisant le ``_callback`` du cœur.

        Celui-ci valide ou annule sa transaction lui-même, ce qu'un test
        n'autorise pas (« Cannot commit or rollback a cursor from inside a
        test »). Le remplacer par un corps inerte laisse justement à
        découvert ce que ce module ajoute autour.
        """
        def stub(record, *args, **kwargs):
            if failure is not None:
                raise failure
            return True

        with patch(CORE_CALLBACK, stub):
            return cron._callback(cron.cron_name, cron.ir_actions_server_id.id)

    def test_success_is_recorded(self):
        with self._patched_env():
            self._call(self.cron)
        run = self.Run.search([("cron_id", "=", self.cron.id)])
        self.assertEqual(len(run), 1)
        self.assertEqual(run.state, "success")
        self.assertEqual(run.cron_name, self.cron.cron_name)
        self.assertFalse(run.error)
        self.assertGreaterEqual(run.duration, 0.0)

    def test_failure_is_recorded_and_reraised(self):
        # Le rattrapage est écrit à la main : ``assertRaises`` d'Odoo pose un
        # point de reprise et l'annule quand l'exception sort, ce qui
        # emporterait justement la ligne que ce test cherche.
        raised = False
        with self._patched_env():
            try:
                self._call(self.cron, failure=ZeroDivisionError("division by zero"))
            except ZeroDivisionError:
                raised = True
        self.assertTrue(raised, "l'échec doit continuer de remonter")
        run = self.Run.search([("cron_id", "=", self.cron.id)])
        self.assertEqual(len(run), 1)
        self.assertEqual(run.state, "failure")
        self.assertIn("ZeroDivisionError", run.error)

    def test_journal_failure_never_blocks_the_cron(self):
        """Une panne du registre laisse la tâche aboutir.

        Le garde-fou entoure l'appel, pas le corps de l'écriture : c'est ce qui
        le rend vérifiable en remplaçant l'écriture elle-même.
        """
        def boom(record, *args, **kwargs):
            raise RuntimeError("registre indisponible")

        with patch.object(type(self.env["ir.cron"]), "_oski_log_run", boom):
            self._call(self.cron)
        self.assertFalse(self.Run.search([("cron_id", "=", self.cron.id)]))

    def test_error_is_truncated(self):
        with self._patched_env():
            try:
                self._call(self.cron, failure=ValueError("x" * 9000))
            except ValueError:
                pass
        run = self.Run.search([("cron_id", "=", self.cron.id)])
        self.assertLessEqual(len(run.error), 4000)

    def test_last_run_is_the_most_recent_per_cron(self):
        other = self.cron.copy({"name": "Autre tâche"})
        now = fields.Datetime.now()
        self.Run.create([
            {"cron_id": self.cron.id, "cron_name": "a", "started_at": now - timedelta(hours=2),
             "state": "success"},
            {"cron_id": self.cron.id, "cron_name": "a", "started_at": now, "state": "failure"},
            {"cron_id": other.id, "cron_name": "b", "started_at": now - timedelta(hours=1),
             "state": "success"},
        ])
        both = self.cron | other
        both.invalidate_recordset()
        self.assertEqual(self.cron.oski_last_state, "failure")
        self.assertEqual(other.oski_last_state, "success")

    def test_history_survives_the_deletion_of_its_cron(self):
        run = self.Run.create({
            "cron_id": self.cron.id, "cron_name": "Tâche de recette",
            "started_at": fields.Datetime.now(), "state": "success"})
        self.cron.unlink()
        self.assertTrue(run.exists())
        self.assertFalse(run.cron_id)
        self.assertEqual(run.cron_name, "Tâche de recette")

    def test_gc_keeps_the_retention_window(self):
        now = fields.Datetime.now()
        old = self.Run.create({"cron_name": "a", "started_at": now - timedelta(days=40),
                               "state": "success"})
        recent = self.Run.create({"cron_name": "a", "started_at": now - timedelta(days=2),
                                  "state": "success"})
        self.Run._gc_oski_cron_runs()
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())

    def test_gc_honours_the_parameter(self):
        now = fields.Datetime.now()
        self.env["ir.config_parameter"].sudo().set_param("oski_cron_monitor.retention_days", "1")
        run = self.Run.create({"cron_name": "a", "started_at": now - timedelta(days=3),
                               "state": "success"})
        self.Run._gc_oski_cron_runs()
        self.assertFalse(run.exists())

    def test_gc_disabled_keeps_everything(self):
        now = fields.Datetime.now()
        self.env["ir.config_parameter"].sudo().set_param("oski_cron_monitor.retention_days", "0")
        run = self.Run.create({"cron_name": "a", "started_at": now - timedelta(days=900),
                               "state": "success"})
        self.Run._gc_oski_cron_runs()
        self.assertTrue(run.exists())

    def test_journal_is_closed_to_ordinary_users(self):
        """``TransactionCase.env`` est superutilisateur : sans ``with_user``,
        aucun droit n'est réellement éprouvé."""
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_cron_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.Run.create({"cron_name": "a", "started_at": fields.Datetime.now(),
                         "state": "success"})
        with self.assertRaises(AccessError):
            self.Run.with_user(user).search([])[:1].read(["cron_name"])
