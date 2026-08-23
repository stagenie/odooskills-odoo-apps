from odoo.tests import TransactionCase


class SchoolCase(TransactionCase):
    """Structure minimale : une période ouverte, un programme collège 2 niveaux."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.period = cls.env['oski.school.period'].create({
            'name': '2026-2027', 'code': '26-27', 'period_type': 'year',
            'date_start': '2026-09-01', 'date_end': '2027-06-30',
        })
        cls.math = cls.env['oski.school.subject'].create({'name': 'Mathematics', 'code': 'MATH'})
        cls.french = cls.env['oski.school.subject'].create({'name': 'French', 'code': 'FR', 'coefficient': 2.0})
        cls.program = cls.env['oski.school.program'].create({
            'name': 'Middle School', 'code': 'MID', 'cycle_type': 'middle',
            'subject_ids': [(6, 0, [cls.math.id, cls.french.id])],
        })
        cls.level_6, cls.level_5 = cls.env['oski.school.level'].create([
            {'program_id': cls.program.id, 'name': 'Grade 6', 'code': 'G6', 'sequence': 1},
            {'program_id': cls.program.id, 'name': 'Grade 5', 'code': 'G5', 'sequence': 2},
        ])
        cls.room = cls.env['oski.school.room'].create({'name': 'Room A', 'code': 'A', 'capacity': 30})
