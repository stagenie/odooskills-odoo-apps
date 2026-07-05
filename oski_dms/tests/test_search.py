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
