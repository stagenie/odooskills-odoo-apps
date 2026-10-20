from psycopg2 import IntegrityError

from odoo.tools import mute_logger

from .common import DmsCommon


class TestTag(DmsCommon):

    def test_create_tag(self):
        # Nom absent des données de démo (« Confidentiel » y existe déjà).
        tag = self.env['oski.dms.tag'].create({'name': 'Étiquette de test'})
        self.assertEqual(tag.name, 'Étiquette de test')

    @mute_logger('odoo.sql_db')
    def test_name_unique(self):
        self.env['oski.dms.tag'].create({'name': 'Juridique'})
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['oski.dms.tag'].create({'name': 'Juridique'})
