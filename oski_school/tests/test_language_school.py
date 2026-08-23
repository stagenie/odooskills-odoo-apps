from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'oski_school')
class TestLanguageSchool(TransactionCase):
    """Spec §7.10 : une école de langues tourne sur le cœur sans code spécifique."""

    def test_rolling_sessions_adult_no_guardian_cefr_promotion(self):
        env = self.env
        english = env['oski.school.subject'].create({'name': 'English', 'code': 'ENG'})
        program = env['oski.school.program'].create({
            'name': 'English courses', 'code': 'ENG', 'cycle_type': 'language',
            'subject_ids': [(6, 0, english.ids)]})
        self.assertFalse(program.guardian_required)
        a1, a2 = env['oski.school.level'].create([
            {'program_id': program.id, 'name': 'A1', 'code': 'A1', 'sequence': 1, 'cefr_code': 'A1'},
            {'program_id': program.id, 'name': 'A2', 'code': 'A2', 'sequence': 2, 'cefr_code': 'A2'},
        ])
        s1 = env['oski.school.period'].create({
            'name': 'Sept', 'code': 'S1', 'period_type': 'session',
            'date_start': '2026-09-01', 'date_end': '2026-10-26'})
        s1.action_open()
        s2 = env['oski.school.period'].create({
            'name': 'Nov', 'code': 'S2', 'period_type': 'session',
            'date_start': '2026-10-27', 'date_end': '2026-12-21'})
        s2.action_open()  # deux sessions ouvertes en même temps
        group_a1 = env['oski.school.class'].create({'level_id': a1.id, 'period_id': s1.id, 'suffix': 'Eve', 'capacity': 12})
        group_a2 = env['oski.school.class'].create({'level_id': a2.id, 'period_id': s2.id, 'suffix': 'Eve', 'capacity': 12})
        adult = env['oski.school.student'].create({
            'partner_id': env['res.partner'].create({'name': 'Adult learner'}).id})
        enr = env['oski.school.enrollment'].create({'student_id': adult.id, 'class_id': group_a1.id})
        enr.action_confirm()
        self.assertEqual(enr.state, 'active', 'session already open → active at once')
        self.assertEqual(adult.billing_partner_id, adult.partner_id)
        wiz = env['oski.school.promotion.wizard'].create({'period_id': s1.id})
        wiz.action_load_lines()
        self.assertEqual(wiz.target_period_id, s2)
        self.assertEqual(wiz.line_ids.target_class_id, group_a2)
        wiz.action_apply()
        self.assertEqual(enr.next_enrollment_id.level_id.cefr_code, 'A2')
        s1.action_close()
        self.assertEqual(enr.state, 'completed')
        self.assertEqual(adult.state, 'active')
