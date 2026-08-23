from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from .common import SchoolCase

@tagged('post_install', '-at_install', 'oski_school')
class TestSecuritySkeleton(TransactionCase):

    def test_groups_chain(self):
        teacher = self.env.ref('oski_school.group_school_teacher')
        officer = self.env.ref('oski_school.group_school_officer')
        manager = self.env.ref('oski_school.group_school_manager')
        self.assertIn(teacher, officer.implied_ids)
        self.assertIn(officer, manager.implied_ids)
        self.assertEqual(teacher.privilege_id, self.env.ref('oski_school.res_groups_privilege_school'))

    def test_student_sequence(self):
        seq = self.env.ref('oski_school.seq_school_student')
        self.assertEqual(seq.code, 'oski.school.student')
        self.assertTrue(seq.prefix)


@tagged('post_install', '-at_install', 'oski_school')
class TestAccess(SchoolCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.user_teacher = Users.create({
            'name': 'T', 'login': 't@x.com', 'partner_id': cls.teacher_partner.id,
            'group_ids': [(6, 0, [cls.env.ref('oski_school.group_school_teacher').id])]})
        cls.teacher.user_id = cls.user_teacher
        cls.user_officer = Users.create({
            'name': 'O', 'login': 'o@x.com',
            'group_ids': [(6, 0, [cls.env.ref('oski_school.group_school_officer').id])]})
        cls.user_manager = Users.create({
            'name': 'M', 'login': 'm@x.com',
            'group_ids': [(6, 0, [cls.env.ref('oski_school.group_school_manager').id])]})
        cls.in_class = cls._new_student('In class', True)
        cls.out_class = cls._new_student('Elsewhere', True)
        cls.env['oski.school.enrollment'].create([
            {'student_id': cls.in_class.id, 'class_id': cls.class_6a.id},
            {'student_id': cls.out_class.id, 'class_id': cls.class_5a.id},
        ]).action_confirm()

    def test_teacher_sees_only_own_classes(self):
        Student = self.env['oski.school.student'].with_user(self.user_teacher)
        names = Student.search([]).mapped('name')
        self.assertIn('In class', names)
        self.assertNotIn('Elsewhere', names)
        Enrollment = self.env['oski.school.enrollment'].with_user(self.user_teacher)
        self.assertEqual(Enrollment.search([]).student_id, self.in_class)

    def test_teacher_cannot_write(self):
        with self.assertRaises(AccessError):
            self.in_class.with_user(self.user_teacher).write({'note': 'x'})
        with self.assertRaises(AccessError):
            self.env['oski.school.period'].with_user(self.user_teacher).create({
                'name': 'x', 'code': 'x', 'period_type': 'year',
                'date_start': '2026-01-01', 'date_end': '2026-12-31'})

    def test_officer_manages_students_not_structure(self):
        s = self.env['oski.school.student'].with_user(self.user_officer).create({
            'partner_id': self.env['res.partner'].create({'name': 'By officer'}).id})
        self.assertTrue(s.registration_number)
        with self.assertRaises(AccessError):
            self.env['oski.school.program'].with_user(self.user_officer).create({
                'name': 'x', 'code': 'x', 'cycle_type': 'middle'})

    def test_manager_runs_promotion(self):
        self.period.action_open()
        wiz = self.env['oski.school.promotion.wizard'].with_user(self.user_manager).create(
            {'period_id': self.period.id})
        wiz.action_load_lines()
        self.assertEqual(len(wiz.line_ids), 2)
        with self.assertRaises(AccessError):
            self.env['oski.school.promotion.wizard'].with_user(self.user_officer).create(
                {'period_id': self.period.id})

    def test_company_isolation(self):
        other = self.env['res.company'].create({'name': 'Other school'})
        self.user_officer.write({'company_ids': [(4, other.id)], 'company_id': other.id})
        Student = self.env['oski.school.student'].with_user(self.user_officer).with_company(other)
        self.assertFalse(Student.search([('id', '=', self.in_class.id)]))

    def test_company_isolation_guardians_terms_lines(self):
        self.env['oski.school.term'].create({
            'period_id': self.period.id, 'name': 'T1', 'sequence': 1,
            'date_start': '2026-09-01', 'date_end': '2026-12-31'})
        other = self.env['res.company'].create({'name': 'Other school 2'})
        self.user_officer.write({'company_ids': [(4, other.id)], 'company_id': other.id})
        Guardian = self.env['oski.school.guardian'].with_user(self.user_officer).with_company(other)
        self.assertFalse(Guardian.search([]), 'guardians of company A leak to company B')
        Term = self.env['oski.school.term'].with_user(self.user_officer).with_company(other)
        self.assertFalse(Term.search([('period_id', '=', self.period.id)]))
        Line = self.env['oski.school.class.subject'].with_user(self.user_officer).with_company(other)
        self.assertFalse(Line.search([('class_id', '=', self.class_6a.id)]))
