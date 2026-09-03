from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase

PASSWORD = "Ceci-Est-Un-Mot-De-Passe-42"


class TestLoginLog(TransactionCase):
    """Les traces sont écrites sur une transaction propre : elles échappent au
    retour arrière du test. Les scénarios les relisent et les effacent donc via
    un curseur neuf."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Le compte doit exister dans la base **validée** : la trace est écrite
        # par un curseur neuf, qui ne verrait pas un utilisateur créé dans la
        # transaction du test — sa clé étrangère partirait dans le vide. On
        # emprunte donc un compte installé, et on lui pose un mot de passe le
        # temps du test.
        cls.user = cls.env.ref("base.user_admin")
        cls.user.password = PASSWORD
        cls.login = cls.user.login

    def setUp(self):
        super().setUp()
        self.addCleanup(self._purge_committed_logs)

    # ------------------------------------------------------------------
    # Lecture et nettoyage hors transaction du test
    # ------------------------------------------------------------------

    def _committed_logs(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env["oski.login.log"].search_read(
                [("login", "=", self.login)],
                ["login", "result", "ip_address", "user_id"],
                order="id",
            )

    def _purge_committed_logs(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["oski.login.log"].search([("login", "=", self.login)]).unlink()

    def _try_login(self, password):
        return self.env["res.users"]._login(
            {"type": "password", "login": self.login, "password": password},
            user_agent_env={"interactive": False},
        )

    # ------------------------------------------------------------------
    # Scénarios
    # ------------------------------------------------------------------

    def test_successful_login_is_recorded(self):
        auth_info = self._try_login(PASSWORD)
        self.assertEqual(auth_info["uid"], self.user.id)
        logs = self._committed_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["result"], "success")
        self.assertEqual(logs[0]["user_id"][0], self.user.id)

    def test_failed_login_survives_the_rollback(self):
        with self.assertRaises(AccessDenied):
            self._try_login("mauvais-mot-de-passe")
        logs = self._committed_logs()
        self.assertEqual(
            len(logs), 1,
            "L'échec annule la transaction de connexion : sa trace doit être "
            "écrite ailleurs, sinon elle disparaît.",
        )
        self.assertEqual(logs[0]["result"], "failure")
        self.assertFalse(logs[0]["user_id"])

    def test_unknown_login_is_recorded_without_user(self):
        self.login = "inconnu.total@example.com"
        with self.assertRaises(AccessDenied):
            self._try_login("peu importe")
        logs = self._committed_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["result"], "failure")
        self.assertFalse(logs[0]["user_id"])

    def test_the_burst_is_visible_line_by_line(self):
        for _ in range(3):
            with self.assertRaises(AccessDenied):
                self._try_login("toujours-faux")
        logs = self._committed_logs()
        self.assertEqual(len(logs), 3)
        self.assertTrue(all(log["result"] == "failure" for log in logs))

    def test_journal_failure_never_blocks_the_login(self):
        """Si le registre tombe, la connexion doit tout de même aboutir."""
        def explode(*args, **kwargs):
            raise RuntimeError("registre indisponible")

        self.patch(type(self.env["res.users"]), "_oski_write_login_log", explode)
        auth_info = self._try_login(PASSWORD)
        self.assertEqual(auth_info["uid"], self.user.id)

    def test_the_journal_is_reserved_to_administrators(self):
        simple = self.env["res.users"].create({
            "name": "Simple", "login": "simple.journal@example.com",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(Exception):
            self.env["oski.login.log"].with_user(simple).search([])
