from odoo import api, fields, models
from odoo.exceptions import UserError


class PromotionWizard(models.TransientModel):
    _name = 'oski.school.promotion.wizard'
    _description = 'Year-end promotion'

    period_id = fields.Many2one('oski.school.period', required=True,
                                domain="[('state', '=', 'open')]")
    target_period_id = fields.Many2one(
        'oski.school.period', compute='_compute_target_period', store=True, readonly=False,
        domain="[('state', '!=', 'closed'), ('id', '!=', period_id)]")
    class_ids = fields.Many2many('oski.school.class', string='Classes',
                                 domain="[('period_id', '=', period_id)]")
    line_ids = fields.One2many('oski.school.promotion.wizard.line', 'wizard_id')
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('period_id')
    def _compute_target_period(self):
        for wiz in self:
            wiz.target_period_id = self.env['oski.school.period'].search([
                ('company_id', '=', wiz.period_id.company_id.id),
                ('period_type', '=', wiz.period_id.period_type),
                ('date_start', '>', wiz.period_id.date_end),
                ('state', '!=', 'closed'),
            ], order='date_start asc', limit=1)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = len(wiz.line_ids)

    # ---- hooks gelés (surchargés par oski_school_grade) ----
    @api.model
    def _get_credits_earned(self, enrollment):
        return 0.0

    @api.model
    def _default_decision(self, enrollment):
        mode = enrollment.program_id.promotion_mode
        if mode == 'level':
            return 'promoted'
        if mode == 'credits':
            required = enrollment.level_id.credits_required
            return 'promoted' if self._get_credits_earned(enrollment) >= required else 'repeated'
        return False

    def _find_target_class(self, enrollment, decision):
        if not self.target_period_id or decision == 'left':
            return self.env['oski.school.class']
        level = enrollment.level_id.next_level_id if decision == 'promoted' else enrollment.level_id
        if not level:
            return self.env['oski.school.class']
        return self.env['oski.school.class'].search([
            ('period_id', '=', self.target_period_id.id), ('level_id', '=', level.id),
            ('state', '=', 'open')], order='name', limit=1)

    def action_load_lines(self):
        self.ensure_one()
        domain = [('period_id', '=', self.period_id.id), ('state', '=', 'active'), ('result', '=', 'none')]
        if self.class_ids:
            domain.append(('class_id', 'in', self.class_ids.ids))
        enrollments = self.env['oski.school.enrollment'].search(domain, order='class_id, student_id')
        self.line_ids.unlink()
        vals = []
        for enr in enrollments:
            decision = self._default_decision(enr)
            vals.append({
                'wizard_id': self.id, 'enrollment_id': enr.id, 'decision': decision,
                'target_class_id': self._find_target_class(enr, decision).id if decision else False,
            })
        self.env['oski.school.promotion.wizard.line'].create(vals)
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        Enrollment = self.env['oski.school.enrollment']
        for line in self.line_ids:
            enr = line.enrollment_id
            if not line.decision:
                raise UserError(self.env._('No decision for %s.', enr.student_id.name))
            needs_target = line.decision in ('promoted', 'repeated') and (
                enr.level_id.next_level_id if line.decision == 'promoted' else True)
            if needs_target and not line.target_class_id:
                raise UserError(self.env._('No target class for %s.', enr.student_id.name))
        for line in self.line_ids:
            enr = line.enrollment_id
            if line.decision == 'left':
                enr.action_withdraw(self.env._('Left at year end'))
                continue
            enr.result = line.decision
            if line.target_class_id:
                new = Enrollment.create({
                    'student_id': enr.student_id.id, 'class_id': line.target_class_id.id,
                    'previous_enrollment_id': enr.id, 'date': self.target_period_id.date_start,
                })
                new.with_context(force_overbook=True).action_confirm()
                enr.next_enrollment_id = new
            enr.student_id.message_post(body=self.env._(
                'Promotion %(period)s: %(decision)s%(target)s',
                period=self.period_id.name, decision=line.decision,
                target=f' → {line.target_class_id.name}' if line.target_class_id else ''))
        return {'type': 'ir.actions.act_window_close'}


class PromotionWizardLine(models.TransientModel):
    _name = 'oski.school.promotion.wizard.line'
    _description = 'Promotion line'
    _order = 'class_id, student_id'

    wizard_id = fields.Many2one('oski.school.promotion.wizard', required=True, ondelete='cascade')
    enrollment_id = fields.Many2one('oski.school.enrollment', required=True)
    student_id = fields.Many2one(related='enrollment_id.student_id')
    class_id = fields.Many2one(related='enrollment_id.class_id')
    level_id = fields.Many2one(related='enrollment_id.level_id')
    decision = fields.Selection([
        ('promoted', 'Promoted'), ('repeated', 'Repeated'), ('left', 'Left')])
    target_class_id = fields.Many2one('oski.school.class')

    @api.onchange('decision')
    def _onchange_decision(self):
        for line in self:
            line.target_class_id = line.wizard_id._find_target_class(line.enrollment_id, line.decision)
