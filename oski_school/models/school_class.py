from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SchoolClass(models.Model):
    _name = 'oski.school.class'
    _description = 'Class'
    _inherit = ['mail.thread']
    _order = 'period_id desc, level_id, name'

    name = fields.Char(compute='_compute_name', store=True, readonly=False)
    suffix = fields.Char(size=8, help='A, B, Morning…')
    level_id = fields.Many2one('oski.school.level', required=True, ondelete='restrict', index=True)
    program_id = fields.Many2one(related='level_id.program_id', store=True, index=True)
    cycle_type = fields.Selection(related='program_id.cycle_type')
    period_id = fields.Many2one('oski.school.period', required=True, ondelete='restrict', index=True)
    room_id = fields.Many2one('oski.school.room')
    homeroom_teacher_id = fields.Many2one('oski.school.teacher', string='Homeroom teacher')
    capacity = fields.Integer(compute='_compute_capacity', store=True, readonly=False)
    student_count = fields.Integer(compute='_compute_counts', store=True)
    seats_available = fields.Integer(compute='_compute_counts', store=True)
    subject_line_ids = fields.One2many('oski.school.class.subject', 'class_id', string='Subjects')
    state = fields.Selection([
        ('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed'),
    ], default='open', required=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    @api.depends('level_id.code', 'period_id.code', 'suffix')
    def _compute_name(self):
        for cls in self:
            if cls.level_id and cls.period_id:
                parts = [cls.level_id.code, cls.period_id.code]
                if cls.suffix:
                    parts.append(cls.suffix)
                cls.name = '/'.join(parts)

    @api.depends('room_id.capacity')
    def _compute_capacity(self):
        for cls in self:
            if cls.room_id and not cls.capacity:
                cls.capacity = cls.room_id.capacity

    def _get_active_enrollments(self):
        """Surchargé en Task 6 : les inscriptions non annulées de la classe."""
        self.ensure_one()
        return self.env['oski.school.class']  # recordset vide de même taille 0

    @api.depends('capacity')
    def _compute_counts(self):
        for cls in self:
            count = len(cls._get_active_enrollments())
            cls.student_count = count
            cls.seats_available = max(cls.capacity - count, 0)

    @api.constrains('level_id', 'period_id', 'company_id')
    def _check_company(self):
        for cls in self:
            if cls.period_id.company_id != cls.company_id or cls.program_id.company_id != cls.company_id:
                raise ValidationError(self.env._(
                    'The class, its period and its program must belong to the same company.'))

    def get_teachers(self):
        return (self.subject_line_ids.teacher_id | self.homeroom_teacher_id)

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})


class SchoolClassSubject(models.Model):
    _name = 'oski.school.class.subject'
    _description = 'Subject taught in a class'
    _order = 'class_id, subject_id'
    _rec_name = 'display_name'

    class_id = fields.Many2one('oski.school.class', required=True, ondelete='cascade', index=True)
    subject_id = fields.Many2one('oski.school.subject', required=True, ondelete='restrict')
    teacher_id = fields.Many2one('oski.school.teacher', ondelete='restrict', index=True)
    coefficient = fields.Float(compute='_compute_coefficient', store=True, readonly=False)
    period_id = fields.Many2one(related='class_id.period_id', store=True)
    company_id = fields.Many2one(related='class_id.company_id', store=True)

    _class_subject_uniq = models.Constraint(
        'UNIQUE (class_id, subject_id)', 'A subject appears once per class.')

    @api.depends('subject_id.coefficient')
    def _compute_coefficient(self):
        for line in self:
            if not line.coefficient:
                line.coefficient = line.subject_id.coefficient

    @api.depends('class_id.name', 'subject_id.name')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f'{line.class_id.name} — {line.subject_id.name}'
