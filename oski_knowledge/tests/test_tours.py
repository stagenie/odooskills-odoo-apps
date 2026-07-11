from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestKnowledgeTours(HttpCase):
    def test_smoke_tour(self):
        # L'admin n'a pas forcément le groupe custom : le granter explicitement.
        self.env.ref('base.user_admin').write({
            'group_ids': [(4, self.env.ref('oski_knowledge.group_knowledge_user').id)]})
        self.start_tour('/odoo', 'oski_knowledge_smoke', login='admin')
