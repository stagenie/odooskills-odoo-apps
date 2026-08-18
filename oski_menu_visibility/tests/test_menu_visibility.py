from odoo.tests.common import TransactionCase


class TestMenuVisibility(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"]
        # Un menu sans action, et sans descendant qui en porte une, est masqué
        # par le cœur lui-même : les feuilles de l'arbre de test doivent donc
        # pointer une action réelle, sinon rien n'est visible et le module
        # semble à tort tout effacer.
        action = cls.env["ir.actions.act_window"].create({
            "name": "Contacts (test menus)",
            "res_model": "res.partner",
            "view_mode": "list,form",
        })
        action_ref = "ir.actions.act_window,%d" % action.id
        cls.root = cls.Menu.create({"name": "Racine OdooSkills"})
        cls.child = cls.Menu.create({"name": "Enfant", "parent_id": cls.root.id})
        cls.grandchild = cls.Menu.create({
            "name": "Petit-enfant", "parent_id": cls.child.id, "action": action_ref,
        })
        cls.other = cls.Menu.create({"name": "Voisin", "action": action_ref})
        cls.tree = cls.root + cls.child + cls.grandchild + cls.other

    def _user(self, login):
        return self.env["res.users"].create({
            "name": login, "login": login,
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

    def _visible_for(self, user):
        return self.tree.with_user(user)._filter_visible_menus()

    def test_nothing_hidden_shows_everything(self):
        user = self._user("rien.masque@example.com")
        self.assertEqual(self._visible_for(user), self.tree)

    def test_hidden_menu_disappears(self):
        user = self._user("masque@example.com")
        user.oski_hidden_menu_ids = self.other
        visible = self._visible_for(user)
        self.assertNotIn(self.other, visible)
        self.assertIn(self.root, visible)

    def test_hiding_a_parent_hides_its_descendants(self):
        user = self._user("branche@example.com")
        user.oski_hidden_menu_ids = self.root
        visible = self._visible_for(user)
        for menu in (self.root, self.child, self.grandchild):
            self.assertNotIn(menu, visible, "%s aurait dû suivre son parent." % menu.name)
        self.assertIn(self.other, visible, "Le voisin n'est pas concerné.")

    def test_hiding_a_middle_node_spares_its_parent(self):
        user = self._user("milieu@example.com")
        user.oski_hidden_menu_ids = self.child
        visible = self._visible_for(user)
        self.assertIn(self.root, visible)
        self.assertNotIn(self.child, visible)
        self.assertNotIn(self.grandchild, visible)

    def test_the_masking_stays_personal(self):
        """Le piège du cache : deux utilisateurs aux mêmes groupes."""
        masked = self._user("cache.a@example.com")
        witness = self._user("cache.b@example.com")
        masked.oski_hidden_menu_ids = self.other
        self.assertNotIn(self.other, self._visible_for(masked))
        self.assertIn(
            self.other, self._visible_for(witness),
            "Un masquage individuel ne doit pas fuir vers un autre utilisateur "
            "partageant les mêmes groupes.",
        )

    def test_unmasking_restores_the_menu(self):
        user = self._user("retour@example.com")
        user.oski_hidden_menu_ids = self.other
        self.assertNotIn(self.other, self._visible_for(user))
        user.oski_hidden_menu_ids = [(5, 0, 0)]
        self.assertIn(self.other, self._visible_for(user))

    def test_load_menus_drops_the_hidden_branch(self):
        user = self._user("chargement@example.com")
        user.oski_hidden_menu_ids = self.root
        loaded = self.Menu.with_user(user).load_menus(False)
        for menu in (self.root, self.child, self.grandchild):
            self.assertNotIn(
                menu.id, loaded,
                "Le menu masqué ne doit pas figurer dans l'arbre servi au navigateur.",
            )

    def test_masking_at_creation_is_taken_into_account(self):
        user = self.env["res.users"].create({
            "name": "Créé masqué", "login": "cree.masque@example.com",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            "oski_hidden_menu_ids": [(6, 0, self.other.ids)],
        })
        self.assertNotIn(self.other, self._visible_for(user))
