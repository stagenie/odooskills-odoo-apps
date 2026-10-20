from datetime import date
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestDuplicate(SchoolCase):

    def setUp(self):
        super().setUp()
        self.env['oski.school.term.generate.wizard'].create({
            'period_id': self.period.id, 'count': 3, 'label': 'Term'}).action_generate()
        self.env['oski.school.enrollment'].create({
            'student_id': self.student.id, 'class_id': self.class_6a.id}).action_confirm()

    def test_default_dates_shifted(self):
        wiz = self.env['oski.school.structure.duplicate.wizard'].with_context(
            default_period_id=self.period.id).create({})
        self.assertEqual(wiz.date_start, date(2027, 9, 1))
        self.assertEqual(wiz.date_end, date(2028, 6, 30))
        self.assertEqual(wiz.name, '2027-2028')
        self.assertEqual(wiz.code, '27-28')

    def test_session_default_dates_follow_duration(self):
        session = self.env['oski.school.period'].create({
            'name': 'EN-S1', 'code': 'ENS1', 'period_type': 'session',
            'date_start': '2026-09-01', 'date_end': '2026-10-26'})
        wiz = self.env['oski.school.structure.duplicate.wizard'].with_context(
            default_period_id=session.id).create({})
        self.assertEqual(wiz.date_start, date(2026, 10, 27))
        self.assertEqual(wiz.date_end, date(2026, 12, 21))

    def test_duplicate_copies_terms_and_classes_without_enrollments(self):
        wiz = self.env['oski.school.structure.duplicate.wizard'].with_context(
            default_period_id=self.period.id).create({})
        action = wiz.action_duplicate()
        new = self.env['oski.school.period'].browse(action['res_id'])
        self.assertEqual(new.state, 'draft')
        self.assertEqual(len(new.term_ids), 3)
        self.assertEqual(new.term_ids[0].date_start, date(2027, 9, 1))
        classes = self.env['oski.school.class'].search([('period_id', '=', new.id)])
        self.assertEqual(len(classes), 2)
        new_6a = classes.filtered(lambda c: c.level_id == self.level_6)
        self.assertEqual(new_6a.room_id, self.room)
        self.assertEqual(new_6a.subject_line_ids.teacher_id, self.teacher)
        self.assertFalse(new_6a.enrollment_ids)
        self.assertEqual(new_6a.name, 'G6/27-28/A')

    def test_no_classes_when_unticked(self):
        wiz = self.env['oski.school.structure.duplicate.wizard'].with_context(
            default_period_id=self.period.id).create({'copy_classes': False})
        new = self.env['oski.school.period'].browse(wiz.action_duplicate()['res_id'])
        self.assertFalse(self.env['oski.school.class'].search([('period_id', '=', new.id)]))
