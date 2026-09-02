from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDevRequest(TransactionCase):

    def _make(self, **kw):
        vals = {
            "requester_name": "Jean Test",
            "email": "jean@test.com",
            "subject": "Module de test",
            "description": "Besoin détaillé",
            "budget_range": "to_discuss",
        }
        vals.update(kw)
        return self.env["oski.dev.request"].create(vals)

    def test_sequence_assigned(self):
        r = self._make()
        self.assertTrue(r.name.startswith("DR"), "Référence doit avoir le préfixe DR")
        self.assertNotEqual(r.name, "New")

    def test_sequence_increment(self):
        r1 = self._make()
        r2 = self._make()
        self.assertNotEqual(r1.name, r2.name)

    def test_defaults(self):
        r = self._make()
        self.assertEqual(r.state, "new")
        self.assertEqual(r.delivery_mode, "store")
        self.assertEqual(r.odoo_version, "19.0")
        self.assertEqual(r.user_id, self.env.user)

    def test_transitions(self):
        r = self._make()
        r.action_set_analysis()
        self.assertEqual(r.state, "analysis")
        r.action_set_quoted()
        self.assertEqual(r.state, "quoted")
        r.action_accept()
        self.assertEqual(r.state, "accepted")
        r.action_set_delivered()
        self.assertEqual(r.state, "delivered")

    def test_reject(self):
        r = self._make()
        r.action_reject()
        self.assertEqual(r.state, "rejected")

    def test_group_expand_shows_all_states(self):
        states = self.env["oski.dev.request"]._group_expand_state([], [])
        self.assertEqual(
            set(states),
            {"new", "analysis", "quoted", "accepted", "rejected", "delivered"},
        )

    def test_exclusive_mode(self):
        r = self._make(delivery_mode="exclusive")
        self.assertEqual(r.delivery_mode, "exclusive")
