from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

OPEN_STATES = ('draft', 'confirmed', 'active')


class SchoolEnrollment(models.Model):
    _name = 'oski.school.enrollment'
    _description = 'Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    student_id = fields.Many2one('oski.school.student', required=True, ondelete='restrict', index=True)
    class_id = fields.Many2one('oski.school.class', required=True, ondelete='restrict', index=True,
                               domain="[('state', '=', 'open')]")
    period_id = fields.Many2one(related='class_id.period_id', store=True, index=True)
    program_id = fields.Many2one(related='class_id.program_id', store=True, index=True)
    level_id = fields.Many2one(related='class_id.level_id', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('active', 'Active'),
        ('completed', 'Completed'), ('withdrawn', 'Withdrawn'),
    ], default='draft', required=True, copy=False, tracking=True, index=True)
    result = fields.Selection([
        ('none', 'Not decided'), ('promoted', 'Promoted'),
        ('repeated', 'Repeated'), ('left', 'Left'),
    ], default='none', required=True, copy=False, tracking=True)
    next_enrollment_id = fields.Many2one('oski.school.enrollment', readonly=True, copy=False)
    previous_enrollment_id = fields.Many2one('oski.school.enrollment', readonly=True, copy=False)
    withdrawal_reason = fields.Char(copy=False)
    company_id = fields.Many2one(related='class_id.company_id', store=True)

    @api.depends('student_id.name', 'class_id.name')
    def _compute_name(self):
        for enr in self:
            enr.name = f'{enr.student_id.name} — {enr.class_id.name}'

    @api.constrains('student_id', 'class_id', 'state')
    def _check_unique_open(self):
        for enr in self.filtered(lambda e: e.state in OPEN_STATES):
            dup = self.search_count([
                ('id', '!=', enr.id), ('student_id', '=', enr.student_id.id),
                ('period_id', '=', enr.period_id.id), ('program_id', '=', enr.program_id.id),
                ('state', 'in', OPEN_STATES)])
            if dup:
                raise ValidationError(self.env._(
                    '%(student)s already has an open enrollment in %(program)s for %(period)s.',
                    student=enr.student_id.name, program=enr.program_id.name, period=enr.period_id.name))

    def action_confirm(self):
        for enr in self:
            if enr.state != 'draft':
                raise UserError(self.env._('Only draft enrollments can be confirmed.'))
            if enr.program_id.guardian_required and not enr.student_id.primary_guardian_id:
                raise ValidationError(self.env._(
                    'The program %s requires a primary guardian on the student.', enr.program_id.name))
            if enr.class_id.seats_available <= 0 and not self.env.context.get('force_overbook'):
                raise ValidationError(self.env._('The class %s is full.', enr.class_id.name))
        self.write({'state': 'confirmed'})
        to_activate = self.filtered(lambda e: e.period_id.state == 'open')
        if to_activate:
            to_activate.action_activate()

    def action_activate(self):
        for enr in self:
            if enr.state != 'confirmed':
                raise UserError(self.env._('Only confirmed enrollments can be activated.'))
            if enr.period_id.state != 'open':
                raise UserError(self.env._('The period %s is not open.', enr.period_id.name))
        self.write({'state': 'active'})

    def action_withdraw(self, reason=None):
        for enr in self:
            if enr.state not in ('confirmed', 'active'):
                raise UserError(self.env._('Only confirmed or active enrollments can be withdrawn.'))
        self.write({'state': 'withdrawn', 'result': 'left',
                    'withdrawal_reason': reason or self.env.context.get('withdrawal_reason')})

    def action_cancel(self):
        if any(e.state != 'draft' for e in self):
            raise UserError(self.env._('Only draft enrollments can be cancelled. Withdraw instead.'))
        self.unlink()

    def action_open_withdraw_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'oski.school.enrollment.withdraw.wizard',
            'view_mode': 'form', 'target': 'new',
            'context': {'default_enrollment_id': self.id},
        }

    def _get_portal_url(self):
        """Provided by oski_school_portal."""
        return False


class SchoolEnrollmentWithdrawWizard(models.TransientModel):
    _name = 'oski.school.enrollment.withdraw.wizard'
    _description = 'Withdraw an enrollment'

    enrollment_id = fields.Many2one('oski.school.enrollment', required=True)
    reason = fields.Char(required=True)

    def action_withdraw(self):
        self.enrollment_id.action_withdraw(self.reason)
        return {'type': 'ir.actions.act_window_close'}
