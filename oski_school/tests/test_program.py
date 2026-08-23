from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestProgram(SchoolCase):

    def test_defaults_by_cycle(self):
        Program = self.env['oski.school.program']
        middle = Program.new({'cycle_type': 'middle'})
        middle._onchange_cycle_type()
        self.assertTrue(middle.guardian_required)
        self.assertEqual(middle.promotion_mode, 'level')
        higher = Program.new({'cycle_type': 'higher'})
        higher._onchange_cycle_type()
        self.assertFalse(higher.guardian_required)
        self.assertEqual(higher.promotion_mode, 'credits')
        language = Program.new({'cycle_type': 'language'})
        language._onchange_cycle_type()
        self.assertFalse(language.guardian_required)
        self.assertEqual(language.promotion_mode, 'level')
        for cycle in ('primary', 'high'):
            p = Program.new({'cycle_type': cycle})
            p._onchange_cycle_type()
            self.assertTrue(p.guardian_required, cycle)
            self.assertEqual(p.promotion_mode, 'level', cycle)
        vocational = Program.new({'cycle_type': 'vocational'})
        vocational._onchange_cycle_type()
        self.assertFalse(vocational.guardian_required)
        self.assertEqual(vocational.promotion_mode, 'manual')
        created = Program.create({'name': 'Voc', 'code': 'VOC', 'cycle_type': 'vocational'})
        self.assertEqual(created.promotion_mode, 'manual', 'defaults also applied on create')

    def test_next_level_follows_sequence(self):
        self.assertEqual(self.level_6.next_level_id, self.level_5)
        self.assertFalse(self.level_5.next_level_id)
        level_4 = self.env['oski.school.level'].create({
            'program_id': self.program.id, 'name': 'Grade 4', 'code': 'G4', 'sequence': 3})
        self.level_5.invalidate_recordset(['next_level_id'])
        self.assertEqual(self.level_5.next_level_id, level_4)

    def test_next_level_manual_override(self):
        self.level_6.next_level_id = False
        self.level_6.manual_next_level = True
        self.level_6.invalidate_recordset(['next_level_id'])
        self.assertFalse(self.level_6.next_level_id)

    def test_level_code_unique_per_program(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['oski.school.level'].create({
                'program_id': self.program.id, 'name': 'Dup', 'code': 'G6', 'sequence': 9})

    def test_subject_coefficient_positive(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['oski.school.subject'].create({'name': 'X', 'code': 'X', 'coefficient': 0})
