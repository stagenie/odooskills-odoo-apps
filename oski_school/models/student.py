from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SchoolStudent(models.Model):
    _name = 'oski.school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    name = fields.Char(related='partner_id.name', store=True, readonly=True)
    email = fields.Char(related='partner_id.email')
    phone = fields.Char(related='partner_id.phone')
    image_128 = fields.Image(related='partner_id.image_128')
    image_1920 = fields.Image(related='partner_id.image_1920', readonly=False)
    registration_number = fields.Char(readonly=True, copy=False, index=True, default='/')
    birth_date = fields.Date()
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    nationality_id = fields.Many2one('res.country')
    id_number = fields.Char(string='ID number')
    guardian_ids = fields.One2many('oski.school.guardian', 'student_id', string='Guardians')
    primary_guardian_id = fields.Many2one(
        'oski.school.guardian', compute='_compute_guardians', store=True)
    billing_partner_id = fields.Many2one(
        'res.partner', compute='_compute_guardians', store=True,
        help='Who receives the invoices: the billing guardian, else the student.')
    state = fields.Selection([
        ('prospect', 'Prospect'), ('active', 'Active'),
        ('alumni', 'Alumni'), ('left', 'Left'),
    ], compute='_compute_state', store=True, tracking=True, index=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    note = fields.Html()
    enrollment_ids = fields.One2many('oski.school.enrollment', 'student_id', string='Enrollments')
    current_enrollment_id = fields.Many2one(
        'oski.school.enrollment', compute='_compute_current_enrollment', store=True)
    current_class_id = fields.Many2one(related='current_enrollment_id.class_id', store=True)
    enrollment_count = fields.Integer(compute='_compute_enrollment_count')

    _partner_uniq = models.Constraint('UNIQUE (partner_id)', 'This contact is already a student.')

    @api.depends('guardian_ids.is_primary', 'guardian_ids.is_billing', 'guardian_ids.partner_id', 'partner_id')
    def _compute_guardians(self):
        for student in self:
            student.primary_guardian_id = student.guardian_ids.filtered('is_primary')[:1]
            billing = student.guardian_ids.filtered('is_billing')[:1]
            student.billing_partner_id = billing.partner_id or student.partner_id

    @api.depends('enrollment_ids.state', 'enrollment_ids.period_id.state')
    def _compute_current_enrollment(self):
        for student in self:
            active = student.enrollment_ids.filtered(lambda e: e.state == 'active')
            student.current_enrollment_id = active.sorted('date', reverse=True)[:1]

    def _compute_enrollment_count(self):
        for student in self:
            student.enrollment_count = len(student.enrollment_ids)

    @api.depends('enrollment_ids.state', 'enrollment_ids.result', 'enrollment_ids.level_id.next_level_id',
                 'enrollment_ids.next_enrollment_id')
    def _compute_state(self):
        for student in self:
            enrollments = student.enrollment_ids
            if not enrollments:
                student.state = 'prospect'
                continue
            if enrollments.filtered(lambda e: e.state in ('active', 'confirmed')):
                student.state = 'active'
                continue
            last = enrollments.sorted(lambda e: (e.date, e.id))[-1]
            if last.state == 'withdrawn':
                student.state = 'left'
            elif last.state == 'completed' and last.result == 'promoted' and not last.level_id.next_level_id:
                student.state = 'alumni'
            elif last.state == 'completed' and last.result == 'left':
                student.state = 'left'
            elif last.state == 'completed':
                student.state = 'alumni' if not last.next_enrollment_id else 'active'
            else:
                student.state = 'prospect'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('registration_number', '/') == '/':
                vals['registration_number'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.school.student') or '/'
        return super().create(vals_list)

    @api.model
    def _get_or_create_from_partner(self, partner, vals):
        student = self.search([('partner_id', '=', partner.id)], limit=1)
        if student:
            return student
        return self.create(dict(vals, partner_id=partner.id))


class SchoolGuardian(models.Model):
    _name = 'oski.school.guardian'
    _description = 'Guardian'
    _order = 'is_primary desc, id'
    _rec_name = 'partner_id'

    student_id = fields.Many2one('oski.school.student', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict')
    relation = fields.Selection([
        ('father', 'Father'), ('mother', 'Mother'), ('legal', 'Legal guardian'), ('other', 'Other'),
    ], required=True, default='other')
    is_primary = fields.Boolean(string='Primary contact')
    is_billing = fields.Boolean(string='Pays the fees')
    has_portal_access = fields.Boolean(compute='_compute_has_portal_access')
    email = fields.Char(related='partner_id.email')
    phone = fields.Char(related='partner_id.phone')
    company_id = fields.Many2one(related='student_id.company_id', store=True, index=True)

    _student_partner_uniq = models.Constraint(
        'UNIQUE (student_id, partner_id)', 'This contact is already a guardian of this student.')

    @api.constrains('is_primary', 'is_billing', 'student_id')
    def _check_single_flags(self):
        for student in self.student_id:
            if len(student.guardian_ids.filtered('is_primary')) > 1:
                raise ValidationError(self.env._('A student has a single primary guardian.'))
            if len(student.guardian_ids.filtered('is_billing')) > 1:
                raise ValidationError(self.env._('A student has a single paying guardian.'))

    def _compute_has_portal_access(self):
        portal = self.env.ref('base.group_portal')
        for guardian in self:
            guardian.has_portal_access = any(
                portal in u.group_ids for u in guardian.partner_id.user_ids)
