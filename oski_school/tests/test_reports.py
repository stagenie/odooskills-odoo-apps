from odoo.exceptions import UserError
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestReports(SchoolCase):

    def setUp(self):
        super().setUp()
        self.enrollment = self.env['oski.school.enrollment'].create({
            'student_id': self.student.id, 'class_id': self.class_6a.id})
        self.enrollment.action_confirm()
        self.period.action_open()

    def test_certificate_html_contains_student_and_class(self):
        report = self.env.ref('oski_school.action_report_enrollment_certificate')
        html = self.env['ir.actions.report']._render_qweb_html(report.id, self.enrollment.ids)[0]
        self.assertIn(b'Sam Student', html)
        self.assertIn(b'G6/26-27/A', html)
        self.assertIn(self.student.registration_number.encode(), html)

    def test_certificate_refused_on_draft(self):
        draft = self.env['oski.school.enrollment'].create({
            'student_id': self._new_student('D', True).id, 'class_id': self.class_6a.id})
        with self.assertRaises(UserError):
            draft.action_print_certificate()

    def test_certificate_pdf(self):
        report = self.env.ref('oski_school.action_report_enrollment_certificate')
        with self.allow_pdf_render():
            pdf, kind = self.env['ir.actions.report'].with_context(
                force_report_rendering=True)._render_qweb_pdf(report.id, self.enrollment.ids)
        self.assertEqual(kind, 'pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_class_list_html(self):
        report = self.env.ref('oski_school.action_report_class_list')
        html = self.env['ir.actions.report']._render_qweb_html(report.id, self.class_6a.ids)[0]
        self.assertIn(b'Sam Student', html)
        self.assertIn(b'Pat Parent', html)
