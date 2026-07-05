from psycopg2 import IntegrityError

from odoo.tools import mute_logger

from .common import DmsCommon


class TestTag(DmsCommon):

    def test_create_tag(self):
        tag = self.env['oski.dms.tag'].create({'name': 'Confidentiel'})
        self.assertEqual(tag.name, 'Confidentiel')

    @mute_logger('odoo.sql_db')
    def test_name_unique(self):
        self.env['oski.dms.tag'].create({'name': 'Juridique'})
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['oski.dms.tag'].create({'name': 'Juridique'})
