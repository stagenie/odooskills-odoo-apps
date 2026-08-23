from lxml import etree
from odoo.tests import tagged
from .common import SchoolCase


@tagged('post_install', '-at_install', 'oski_school')
class TestViews(SchoolCase):
    """Les défauts d'écran n'apparaissent qu'à l'écran : on lit l'arch servie."""

    def _arch(self, model, xmlid):
        view = self.env.ref(xmlid)
        arch = self.env[model].get_view(view.id, 'form')['arch']
        return etree.fromstring(arch)

    def _assert_anchors(self, tree, buttons):
        self.assertTrue(tree.xpath('//header'))
        self.assertTrue(tree.xpath("//div[@name='button_box']"))
        self.assertTrue(tree.xpath("//notebook/page[@name='main']"))
        for name in buttons:
            self.assertTrue(tree.xpath(f"//header/button[@name='{name}']"), f'button {name} missing')

    def test_enrollment_form(self):
        tree = self._arch('oski.school.enrollment', 'oski_school.view_school_enrollment_form')
        self._assert_anchors(tree, ['action_confirm', 'action_activate', 'action_open_withdraw_wizard', 'action_cancel'])
        self.assertTrue(tree.xpath("//field[@name='state'][@widget='statusbar']"))

    def test_student_form(self):
        tree = self._arch('oski.school.student', 'oski_school.view_school_student_form')
        self._assert_anchors(tree, [])
        self.assertTrue(tree.xpath("//field[@name='guardian_ids']"))
        self.assertTrue(tree.xpath("//field[@name='registration_number']"))

    def test_class_form(self):
        tree = self._arch('oski.school.class', 'oski_school.view_school_class_form')
        self._assert_anchors(tree, ['action_open', 'action_close'])
        self.assertTrue(tree.xpath("//field[@name='subject_line_ids']"))

    def test_period_form_has_wizard_buttons(self):
        tree = self._arch('oski.school.period', 'oski_school.view_school_period_form')
        for name in ('action_open', 'action_close', 'action_open_promotion_wizard',
                     'action_open_duplicate_wizard', 'action_open_term_wizard'):
            self.assertTrue(tree.xpath(f"//header/button[@name='{name}']"), name)

    def test_no_legacy_syntax(self):
        views = self.env['ir.ui.view'].search([('model', 'like', 'oski.school.%')])
        for view in views:
            self.assertNotIn('attrs=', view.arch_db, view.name)
            self.assertNotIn('states=', view.arch_db, view.name)
            self.assertNotIn('<tree', view.arch_db, view.name)

    def test_actions_list_not_tree(self):
        for xmlid in ('action_school_student', 'action_school_enrollment', 'action_school_class',
                      'action_school_period', 'action_school_program', 'action_school_teacher',
                      'action_school_subject', 'action_school_room'):
            action = self.env.ref(f'oski_school.{xmlid}')
            self.assertNotIn('tree', action.view_mode, xmlid)
            self.assertIn('list', action.view_mode, xmlid)
