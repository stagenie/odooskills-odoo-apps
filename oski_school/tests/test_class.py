from odoo.exceptions import ValidationError
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestClass(SchoolCase):

    def test_name_computed(self):
        self.assertEqual(self.class_6a.name, 'G6/26-27/A')
        self.class_6a.name = 'Sixième A'
        self.assertEqual(self.class_6a.name, 'Sixième A')

    def test_program_related(self):
        self.assertEqual(self.class_6a.program_id, self.program)

    def test_capacity_default_from_room(self):
        c = self.env['oski.school.class'].create({
            'level_id': self.level_6.id, 'period_id': self.period.id, 'suffix': 'B',
            'room_id': self.room.id})
        self.assertEqual(c.capacity, 30)

    def test_seats_without_enrollments(self):
        self.assertEqual(self.class_6a.student_count, 0)
        self.assertEqual(self.class_6a.seats_available, 2)

    def test_get_teachers(self):
        self.assertEqual(self.class_6a.get_teachers(), self.teacher)
        other = self.env['oski.school.teacher'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Homeroom'}).id})
        self.class_6a.homeroom_teacher_id = other
        self.assertEqual(self.class_6a.get_teachers(), self.teacher | other)

    def test_subject_line_unique(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env['oski.school.class.subject'].create({
                'class_id': self.class_6a.id, 'subject_id': self.math.id, 'teacher_id': self.teacher.id})

    def test_company_consistency(self):
        other_company = self.env['res.company'].create({'name': 'Other school'})
        period = self.env['oski.school.period'].with_company(other_company).create({
            'name': 'X', 'code': 'X', 'period_type': 'year',
            'date_start': '2026-09-01', 'date_end': '2027-06-30',
            'company_id': other_company.id})
        with self.assertRaises(ValidationError):
            self.env['oski.school.class'].create({
                'level_id': self.level_6.id, 'period_id': period.id, 'suffix': 'Z'})
