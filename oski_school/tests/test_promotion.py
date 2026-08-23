from odoo.exceptions import UserError
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestPromotion(SchoolCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.class_6a.capacity = 10
        cls.students = [cls._new_student(f'S{i}', True) for i in range(3)]
        cls.enrollments = cls.env['oski.school.enrollment'].create([
            {'student_id': s.id, 'class_id': cls.class_6a.id} for s in cls.students])
        cls.enrollments.action_confirm()
        cls.period.action_open()
        cls.next_period = cls.env['oski.school.period'].create({
            'name': '2027-2028', 'code': '27-28', 'period_type': 'year',
            'date_start': '2027-09-01', 'date_end': '2028-06-30'})
        cls.next_6a, cls.next_5a = cls.env['oski.school.class'].create([
            {'level_id': cls.level_6.id, 'period_id': cls.next_period.id, 'suffix': 'A', 'capacity': 30},
            {'level_id': cls.level_5.id, 'period_id': cls.next_period.id, 'suffix': 'A', 'capacity': 30},
        ])

    def _wizard(self):
        wiz = self.env['oski.school.promotion.wizard'].create({'period_id': self.period.id})
        wiz.action_load_lines()
        return wiz

    def test_target_period_defaults_to_next(self):
        wiz = self._wizard()
        self.assertEqual(wiz.target_period_id, self.next_period)

    def test_lines_proposed_by_level_mode(self):
        wiz = self._wizard()
        self.assertEqual(len(wiz.line_ids), 3)
        self.assertTrue(all(l.decision == 'promoted' for l in wiz.line_ids))
        self.assertTrue(all(l.target_class_id == self.next_5a for l in wiz.line_ids))

    def test_credits_mode_uses_hook(self):
        self.program.promotion_mode = 'credits'
        self.level_6.credits_required = 30
        wiz = self._wizard()
        # le cœur retourne 0 crédit → personne n'est promu
        self.assertTrue(all(l.decision == 'repeated' for l in wiz.line_ids))
        self.assertTrue(all(l.target_class_id == self.next_6a for l in wiz.line_ids))

    def test_manual_mode_leaves_decision_empty(self):
        self.program.promotion_mode = 'manual'
        wiz = self._wizard()
        self.assertTrue(all(not l.decision for l in wiz.line_ids))

    def test_apply_creates_linked_enrollments(self):
        wiz = self._wizard()
        lines = wiz.line_ids.sorted('id')
        lines[1].decision = 'repeated'
        lines[1].target_class_id = self.next_6a
        lines[2].decision = 'left'
        wiz.action_apply()
        e0, e1, e2 = self.enrollments
        self.assertEqual((e0.result, e1.result, e2.result), ('promoted', 'repeated', 'left'))
        self.assertEqual(e0.next_enrollment_id.class_id, self.next_5a)
        self.assertEqual(e0.next_enrollment_id.state, 'confirmed')
        self.assertEqual(e0.next_enrollment_id.previous_enrollment_id, e0)
        self.assertEqual(e1.next_enrollment_id.class_id, self.next_6a)
        self.assertFalse(e2.next_enrollment_id)
        self.assertEqual(e2.state, 'withdrawn')
        self.assertEqual(self.students[2].state, 'left')

    def test_apply_refuses_undecided_line(self):
        self.program.promotion_mode = 'manual'
        wiz = self._wizard()
        with self.assertRaises(UserError):
            wiz.action_apply()

    def test_apply_refuses_missing_target_class(self):
        wiz = self._wizard()
        wiz.line_ids[0].target_class_id = False
        with self.assertRaises(UserError):
            wiz.action_apply()

    def test_last_level_promoted_becomes_alumni(self):
        # Déplace les 3 inscriptions en 5e (dernier niveau).
        self.class_5a.capacity = 10
        for e in self.enrollments:
            e.action_withdraw('move')
        last = self.env['oski.school.enrollment'].create([
            {'student_id': s.id, 'class_id': self.class_5a.id} for s in self.students])
        last.action_confirm()
        wiz = self._wizard()
        self.assertEqual(len(wiz.line_ids), 3)
        self.assertTrue(all(not l.target_class_id for l in wiz.line_ids))
        wiz.action_apply()
        self.assertTrue(all(e.result == 'promoted' for e in last))
        self.assertFalse(last.next_enrollment_id)
        self.period.action_close()
        self.assertTrue(all(e.state == 'completed' for e in last))
        self.assertTrue(all(s.state == 'alumni' for s in self.students))

    def test_rerun_excludes_decided(self):
        wiz = self._wizard()
        wiz.line_ids[0].decision = 'left'
        wiz.line_ids[1:].unlink()
        wiz.action_apply()
        again = self._wizard()
        self.assertEqual(len(again.line_ids), 2)

    def test_close_refuses_undecided_then_completes(self):
        with self.assertRaises(UserError):
            self.period.action_close()
        wiz = self._wizard()
        wiz.action_apply()
        self.period.action_close()
        self.assertTrue(all(e.state == 'completed' for e in self.enrollments))
        self.assertEqual(self.period.state, 'closed')
