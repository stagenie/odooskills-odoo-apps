from odoo.tests.common import TransactionCase


class DmsCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workspace = cls.env['oski.dms.workspace']
        cls.ws_root = cls.Workspace.create({'name': 'Général'})
        cls.ws_child = cls.Workspace.create({
            'name': 'Contrats', 'parent_id': cls.ws_root.id,
        })

    @classmethod
    def _make_user(cls, login, groups_xmlids):
        """Crée un utilisateur de test membre des groupes donnés (xmlids)."""
        groups = [(4, cls.env.ref(x).id) for x in groups_xmlids]
        return cls.env['res.users'].create({
            'name': login, 'login': login, 'email': f'{login}@test.com',
            'group_ids': groups,
        })
