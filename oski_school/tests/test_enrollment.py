from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestEnrollment(SchoolCase):

    def _enroll(self, student, klass=None, **vals):
        return self.env['oski.school.enrollment'].create(dict(
            {'student_id': student.id, 'class_id': (klass or self.class_6a).id}, **vals))

    def test_related_fields(self):
        enr = self._enroll(self.student)
        self.assertEqual(enr.period_id, self.period)
        self.assertEqual(enr.program_id, self.program)
        self.assertEqual(enr.level_id, self.level_6)
        self.assertEqual(enr.state, 'draft')
        self.assertIn('Sam Student', enr.name)

    def test_confirm_requires_guardian_when_program_says_so(self):
        orphan = self._new_student('No guardian')
        enr = self._enroll(orphan)
        with self.assertRaises(ValidationError):
            enr.action_confirm()
        self.program.guardian_required = False
        enr.action_confirm()
        self.assertEqual(enr.state, 'confirmed')

    def test_confirm_checks_seats(self):
        a = self._enroll(self._new_student('A', True)); a.action_confirm()
        b = self._enroll(self._new_student('B', True)); b.action_confirm()
        self.assertEqual(self.class_6a.seats_available, 0)
        c = self._enroll(self._new_student('C', True))
        with self.assertRaises(ValidationError):
            c.action_confirm()
        c.with_context(force_overbook=True).action_confirm()
        self.assertEqual(c.state, 'confirmed')

    def test_unique_per_period_and_program(self):
        self._enroll(self.student)
        with self.assertRaises(ValidationError):
            self._enroll(self.student, self.class_5a)

    def test_withdrawn_frees_the_unicity_and_the_seat(self):
        enr = self._enroll(self.student)
        enr.action_confirm()
        enr.action_withdraw('Moved away')
        self.assertEqual(enr.state, 'withdrawn')
        self.assertEqual(enr.withdrawal_reason, 'Moved away')
        self.assertEqual(self.class_6a.seats_available, 2)
        again = self._enroll(self.student, self.class_5a)
        self.assertEqual(again.state, 'draft')

    def test_period_open_activates_confirmed(self):
        enr = self._enroll(self.student)
        enr.action_confirm()
        self.assertEqual(enr.state, 'confirmed')
        self.period.action_open()
        self.assertEqual(enr.state, 'active')
        self.assertEqual(self.student.state, 'active')

    def test_activate_refused_on_draft_period(self):
        enr = self._enroll(self.student)
        enr.action_confirm()
        with self.assertRaises(UserError):
            enr.action_activate()

    def test_cancel_only_draft(self):
        enr = self._enroll(self.student)
        enr.action_confirm()
        with self.assertRaises(UserError):
            enr.action_cancel()

    def test_student_state_follows_enrollments(self):
        self.assertEqual(self.student.state, 'prospect')
        enr = self._enroll(self.student)
        enr.action_confirm()
        self.period.action_open()
        self.assertEqual(self.student.state, 'active')
        enr.action_withdraw('Left')
        self.assertEqual(self.student.state, 'left')

    def test_cycle_type_locked_after_enrollment(self):
        self.program.cycle_type = 'high'
        self._enroll(self.student)
        with self.assertRaises(ValidationError):
            self.program.cycle_type = 'language'

    def test_program_enrollment_count(self):
        self._enroll(self.student)
        self.program.invalidate_recordset(['enrollment_count'])
        self.assertEqual(self.program.enrollment_count, 1)

    def test_portal_url_hook_is_false_in_core(self):
        self.assertFalse(self._enroll(self.student)._get_portal_url())

    def test_capacity_zero_is_unlimited(self):
        klass = self.env['oski.school.class'].create({
            'level_id': self.level_6.id, 'period_id': self.period.id, 'suffix': 'C'})
        self.assertEqual(klass.capacity, 0)
        for i in range(3):
            student = self._new_student(f'Unlimited{i}', True)
            enr = self._enroll(student, klass)
            enr.action_confirm()
        self.assertEqual(klass.student_count, 3)

    def test_cancel_returns_action(self):
        enr = self._enroll(self.student)
        action = enr.action_cancel()
        self.assertEqual(action.get('res_model'), 'oski.school.enrollment')
