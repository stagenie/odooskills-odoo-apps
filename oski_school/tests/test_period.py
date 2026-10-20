from datetime import date, timedelta
from freezegun import freeze_time
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestPeriod(SchoolCase):

    def test_dates_order(self):
        with self.assertRaises(ValidationError):
            self.env['oski.school.period'].create({
                'name': 'Bad', 'code': 'BAD', 'period_type': 'year',
                'date_start': '2027-01-01', 'date_end': '2026-01-01',
            })

    def test_state_flow(self):
        self.assertEqual(self.period.state, 'draft')
        self.period.action_open()
        self.assertEqual(self.period.state, 'open')
        self.period.action_close()
        self.assertEqual(self.period.state, 'closed')

    @freeze_time('2026-10-15')
    def test_is_current_and_get_current(self):
        self.assertFalse(self.period.is_current, 'draft is never current')
        self.period.action_open()
        self.period.invalidate_recordset(['is_current'])
        self.assertTrue(self.period.is_current)
        self.assertEqual(
            self.env['oski.school.period'].get_current(self.company, 'year'), self.period)
        self.assertFalse(self.env['oski.school.period'].get_current(self.company, 'session'))

    def test_several_open_periods_allowed(self):
        self.period.action_open()
        other = self.env['oski.school.period'].create({
            'name': 'EN-S1', 'code': 'ENS1', 'period_type': 'session',
            'date_start': '2026-09-01', 'date_end': '2026-10-30',
        })
        other.action_open()
        self.assertEqual(other.state, 'open')

    def test_generate_terms_splits_dates(self):
        wiz = self.env['oski.school.term.generate.wizard'].create({
            'period_id': self.period.id, 'count': 3, 'label': 'Term',
        })
        wiz.action_generate()
        terms = self.period.term_ids.sorted('sequence')
        self.assertEqual(len(terms), 3)
        self.assertEqual(terms[0].name, 'Term 1')
        self.assertEqual(terms[0].date_start, date(2026, 9, 1))
        self.assertEqual(terms[-1].date_end, date(2027, 6, 30))
        for a, b in zip(terms, terms[1:]):
            self.assertEqual(b.date_start, a.date_end + timedelta(days=1))

    def test_generate_refuses_when_terms_exist(self):
        self.env['oski.school.term'].create({
            'period_id': self.period.id, 'name': 'T1', 'sequence': 1,
            'date_start': '2026-09-01', 'date_end': '2026-12-31'})
        wiz = self.env['oski.school.term.generate.wizard'].create({
            'period_id': self.period.id, 'count': 2, 'label': 'Term'})
        with self.assertRaises(ValidationError):
            wiz.action_generate()
