from odoo.exceptions import ValidationError
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestStudent(SchoolCase):

    def test_registration_number_from_sequence(self):
        self.assertTrue(self.student.registration_number.startswith('STU/'))
        other = self._new_student('Other')
        self.assertNotEqual(other.registration_number, self.student.registration_number)

    def test_name_is_partner_name(self):
        self.assertEqual(self.student.name, 'Sam Student')
        self.student_partner.name = 'Sam Renamed'
        self.assertEqual(self.student.name, 'Sam Renamed')

    def test_one_student_per_partner(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env['oski.school.student'].create({'partner_id': self.student_partner.id})

    def test_partner_cannot_be_deleted(self):
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.student_partner.unlink()

    def test_primary_and_billing_guardian(self):
        self.assertEqual(self.student.primary_guardian_id, self.guardian)
        self.assertEqual(self.student.billing_partner_id, self.parent_partner)
        second = self.env['res.partner'].create({'name': 'Second parent'})
        with self.assertRaises(ValidationError):
            self.env['oski.school.guardian'].create({
                'student_id': self.student.id, 'partner_id': second.id,
                'relation': 'father', 'is_primary': True})

    def test_billing_falls_back_to_student(self):
        lone = self._new_student('Lone adult')
        self.assertEqual(lone.billing_partner_id, lone.partner_id)
        self.assertFalse(lone.primary_guardian_id)

    def test_same_partner_student_and_guardian(self):
        # Un adulte étudiant en langues peut être tuteur de son enfant au collège.
        child = self._new_student('Child')
        g = self.env['oski.school.guardian'].create({
            'student_id': child.id, 'partner_id': self.student_partner.id,
            'relation': 'father', 'is_primary': True})
        self.assertEqual(g.partner_id, self.student.partner_id)

    def test_get_or_create_from_partner(self):
        Student = self.env['oski.school.student']
        same = Student._get_or_create_from_partner(self.student_partner, {})
        self.assertEqual(same, self.student)
        p = self.env['res.partner'].create({'name': 'Brand new'})
        created = Student._get_or_create_from_partner(p, {'birth_date': '2010-01-01'})
        self.assertEqual(created.partner_id, p)
        self.assertEqual(str(created.birth_date), '2010-01-01')

    def test_teacher_name_and_user_group(self):
        self.assertEqual(self.teacher.name, 'Ada Teacher')
        user = self.env['res.users'].create({
            'name': 'Ada', 'login': 'ada@example.com', 'partner_id': self.teacher_partner.id})
        self.teacher.user_id = user
        self.assertIn(self.env.ref('oski_school.group_school_teacher'), user.group_ids)
