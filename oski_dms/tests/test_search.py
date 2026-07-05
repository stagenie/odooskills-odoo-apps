import base64
from .common import DmsCommon


class TestSearch(DmsCommon):

    def test_group_by_workspace(self):
        self.env['oski.dms.document'].create({
            'name': 'A', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(b'a'), 'file_name': 'a.txt',
        })
        self.env['oski.dms.document'].create({
            'name': 'B', 'workspace_id': self.ws_child.id,
            'file': base64.b64encode(b'b'), 'file_name': 'b.txt',
        })
        groups = self.env['oski.dms.document']._read_group(
            [], groupby=['workspace_id'], aggregates=['__count'])
        counts = {ws.id: c for ws, c in groups}
        self.assertEqual(counts.get(self.ws_root.id), 1)
        self.assertEqual(counts.get(self.ws_child.id), 1)

    def test_res_name_not_searchable(self):
        # `res_name` est un compute store=False sans paramètre `search=` :
        # non recherchable. Il a été retiré de la vue search car un facet
        # texte dessus produirait `[('res_name', 'ilike', ...)]` → plantage
        # `ValueError: Cannot convert ... to SQL because it is not stored`.
        # Il reste affiché en colonne/form, seulement pas comme critère libre.
        field = self.env['oski.dms.document']._fields['res_name']
        self.assertFalse(field.store)
        self.assertFalse(field.search)
        # Les critères de recherche réels restent fonctionnels.
        self.env['oski.dms.document'].create({
            'name': 'Rapport', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(b'r'), 'file_name': 'r.txt',
        })
        self.assertTrue(
            self.env['oski.dms.document'].search([('name', 'ilike', 'Rapport')]))
