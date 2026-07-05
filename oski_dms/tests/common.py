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
