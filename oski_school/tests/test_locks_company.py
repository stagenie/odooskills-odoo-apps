from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestCompanyConsistency(SchoolCase):
    """Les données d'élèves d'une société ne doivent jamais se mélanger à celles d'une autre."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = cls.env['res.company'].create({'name': 'Other school'})
        Env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.other.id, cls.company.id]))
        cls.env = Env
        cls.other_student = cls.env['oski.school.student'].create({
            'partner_id': cls.env['res.partner'].create({'name': 'Other pupil'}).id,
            'company_id': cls.other.id})
        cls.other_teacher = cls.env['oski.school.teacher'].create({
            'partner_id': cls.env['res.partner'].create({'name': 'Other teacher'}).id,
            'company_id': cls.other.id})

    def test_level_hidden_to_other_company(self):
        Users = self.env['res.users'].with_context(no_reset_password=True)
        user = Users.create({
            'name': 'B', 'login': 'b@x.com', 'company_id': self.other.id,
            'company_ids': [(6, 0, [self.other.id])],
            'group_ids': [(6, 0, [self.env.ref('oski_school.group_school_teacher').id])]})
        Level = self.env['oski.school.level'].with_user(user).with_context(
            allowed_company_ids=[self.other.id])
        self.assertFalse(Level.search([('id', '=', self.level_6.id)]),
                         'levels of company A leak to company B')

    def test_enrollment_student_of_other_company(self):
        with self.assertRaises(UserError):
            self.env['oski.school.enrollment'].create({
                'student_id': self.other_student.id, 'class_id': self.class_6a.id})

    def test_class_teacher_of_other_company(self):
        with self.assertRaises(UserError):
            self.class_5a.homeroom_teacher_id = self.other_teacher
        with self.assertRaises(UserError):
            self.env['oski.school.class.subject'].create({
                'class_id': self.class_5a.id, 'subject_id': self.math.id,
                'teacher_id': self.other_teacher.id})


@tagged('post_install', '-at_install', 'oski_school')
class TestStateLocks(SchoolCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.enr = cls.env['oski.school.enrollment'].create({
            'student_id': cls.student.id, 'class_id': cls.class_6a.id})
        cls.enr.action_confirm()

    def test_confirmed_enrollment_keeps_student_and_class(self):
        with self.assertRaises(UserError):
            self.enr.class_id = self.class_5a
        with self.assertRaises(UserError):
            self.enr.student_id = self._new_student('Swap')
        self.enr.withdrawal_reason = 'other fields stay editable'

    def test_confirmed_enrollment_not_deletable(self):
        with self.assertRaises(UserError):
            self.enr.unlink()

    def test_no_confirmation_in_closed_class(self):
        self.class_5a.action_close()
        enr = self.env['oski.school.enrollment'].create({
            'student_id': self._new_student('Late', True).id, 'class_id': self.class_5a.id})
        with self.assertRaises(UserError):
            enr.action_confirm()

    def test_closed_period_stays_closed(self):
        self.enr.action_withdraw('moved')
        self.period.action_open()
        self.period.action_close()
        with self.assertRaises(UserError):
            self.period.action_open()
        wiz = self.env['oski.school.promotion.wizard'].create({'period_id': self.period.id})
        with self.assertRaises(UserError):
            wiz.action_apply()
