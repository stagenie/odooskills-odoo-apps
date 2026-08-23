from odoo.tests import TransactionCase, tagged


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
