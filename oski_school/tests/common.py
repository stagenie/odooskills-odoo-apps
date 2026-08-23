from odoo.tests import TransactionCase


class SchoolCase(TransactionCase):
    """Structure minimale : une période ouverte, un programme collège 2 niveaux."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.period = cls.env['oski.school.period'].create({
            'name': '2026-2027', 'code': '26-27', 'period_type': 'year',
            'date_start': '2026-09-01', 'date_end': '2027-06-30',
        })
        cls.math = cls.env['oski.school.subject'].create({'name': 'Mathematics', 'code': 'MATH'})
        cls.french = cls.env['oski.school.subject'].create({'name': 'French', 'code': 'FR', 'coefficient': 2.0})
        cls.program = cls.env['oski.school.program'].create({
            'name': 'Middle School', 'code': 'MID', 'cycle_type': 'middle',
            'subject_ids': [(6, 0, [cls.math.id, cls.french.id])],
        })
        cls.level_6, cls.level_5 = cls.env['oski.school.level'].create([
            {'program_id': cls.program.id, 'name': 'Grade 6', 'code': 'G6', 'sequence': 1},
            {'program_id': cls.program.id, 'name': 'Grade 5', 'code': 'G5', 'sequence': 2},
        ])
        cls.room = cls.env['oski.school.room'].create({'name': 'Room A', 'code': 'A', 'capacity': 30})
        cls.teacher_partner = cls.env['res.partner'].create({'name': 'Ada Teacher'})
        cls.teacher = cls.env['oski.school.teacher'].create({
            'partner_id': cls.teacher_partner.id, 'subject_ids': [(6, 0, [cls.math.id])]})
        cls.student_partner = cls.env['res.partner'].create({'name': 'Sam Student'})
        cls.student = cls.env['oski.school.student'].create({
            'partner_id': cls.student_partner.id, 'birth_date': '2014-03-02'})
        cls.parent_partner = cls.env['res.partner'].create({'name': 'Pat Parent', 'email': 'pat@example.com'})
        cls.guardian = cls.env['oski.school.guardian'].create({
            'student_id': cls.student.id, 'partner_id': cls.parent_partner.id,
            'relation': 'mother', 'is_primary': True, 'is_billing': True})
        cls.class_6a = cls.env['oski.school.class'].create({
            'level_id': cls.level_6.id, 'period_id': cls.period.id, 'suffix': 'A',
            'room_id': cls.room.id, 'capacity': 2,
            'subject_line_ids': [(0, 0, {'subject_id': cls.math.id, 'teacher_id': cls.teacher.id})],
        })
        cls.class_5a = cls.env['oski.school.class'].create({
            'level_id': cls.level_5.id, 'period_id': cls.period.id, 'suffix': 'A', 'capacity': 30})

    @classmethod
    def _new_student(cls, name, with_guardian=False):
        partner = cls.env['res.partner'].create({'name': name})
        student = cls.env['oski.school.student'].create({'partner_id': partner.id})
        if with_guardian:
            gp = cls.env['res.partner'].create({'name': f'{name} parent'})
            cls.env['oski.school.guardian'].create({
                'student_id': student.id, 'partner_id': gp.id,
                'relation': 'father', 'is_primary': True, 'is_billing': True})
        return student
