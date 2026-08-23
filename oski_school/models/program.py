from odoo import api, fields, models
from odoo.exceptions import ValidationError

CYCLE_TYPES = [
    ('primary', 'Primary'), ('middle', 'Middle school'), ('high', 'High school'),
    ('higher', 'Higher education'), ('language', 'Language school'),
    ('vocational', 'Vocational training'),
]
CYCLE_DEFAULTS = {
    'primary': {'guardian_required': True, 'promotion_mode': 'level'},
    'middle': {'guardian_required': True, 'promotion_mode': 'level'},
    'high': {'guardian_required': True, 'promotion_mode': 'level'},
    'higher': {'guardian_required': False, 'promotion_mode': 'credits'},
    'language': {'guardian_required': False, 'promotion_mode': 'level'},
    'vocational': {'guardian_required': False, 'promotion_mode': 'manual'},
}


class SchoolSubject(models.Model):
    _name = 'oski.school.subject'
    _description = 'School Subject'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=16)
    credits = fields.Float(default=0.0)
    coefficient = fields.Float(default=1.0, required=True)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint('UNIQUE (code)', 'The subject code must be unique.')

    @api.constrains('coefficient')
    def _check_coefficient(self):
        if any(s.coefficient <= 0 for s in self):
            raise ValidationError(self.env._('The coefficient must be positive.'))


class SchoolRoom(models.Model):
    _name = 'oski.school.room'
    _description = 'School Room'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, size=16)
    capacity = fields.Integer(default=30)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        'UNIQUE (code, company_id)', 'The room code must be unique per company.')


class SchoolProgram(models.Model):
    _name = 'oski.school.program'
    _description = 'School Program'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(required=True, size=16)
    cycle_type = fields.Selection(CYCLE_TYPES, required=True, default='middle', tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    level_ids = fields.One2many('oski.school.level', 'program_id', string='Levels')
    subject_ids = fields.Many2many('oski.school.subject', string='Subjects')
    guardian_required = fields.Boolean(default=True)
    promotion_mode = fields.Selection([
        ('level', 'Next level'), ('credits', 'By credits'), ('manual', 'Manual'),
    ], required=True, default='level')
    active = fields.Boolean(default=True)
    description = fields.Html(translate=True)
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    image_128 = fields.Image('Thumbnail', related='image_1920', max_width=128, max_height=128, store=True)
    enrollment_ids = fields.One2many('oski.school.enrollment', 'program_id')
    enrollment_count = fields.Integer(compute='_compute_enrollment_count')
    level_count = fields.Integer(compute='_compute_level_count')

    _code_company_uniq = models.Constraint(
        'UNIQUE (code, company_id)', 'The program code must be unique per company.')

    @api.onchange('cycle_type')
    def _onchange_cycle_type(self):
        for program in self:
            program.update(CYCLE_DEFAULTS.get(program.cycle_type, {}))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            defaults = CYCLE_DEFAULTS.get(vals.get('cycle_type', 'middle'), {})
            for key, value in defaults.items():
                vals.setdefault(key, value)
        return super().create(vals_list)

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for program in self:
            program.enrollment_count = len(program.enrollment_ids)

    @api.depends('level_ids')
    def _compute_level_count(self):
        for program in self:
            program.level_count = len(program.level_ids)

    def write(self, vals):
        if 'cycle_type' in vals:
            locked = self.filtered(lambda p: p.enrollment_ids and p.cycle_type != vals['cycle_type'])
            if locked:
                raise ValidationError(self.env._(
                    'The cycle type of %s is locked: students are already enrolled.', locked[0].name))
        return super().write(vals)


class SchoolLevel(models.Model):
    _name = 'oski.school.level'
    _description = 'School Level'
    _order = 'program_id, sequence, id'

    program_id = fields.Many2one('oski.school.program', required=True, ondelete='cascade')
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=16)
    sequence = fields.Integer(default=10)
    manual_next_level = fields.Boolean(
        help='Tick to set the next level by hand instead of following the sequence.')
    next_level_id = fields.Many2one(
        'oski.school.level', compute='_compute_next_level', store=True, readonly=False,
        domain="[('program_id', '=', program_id), ('id', '!=', id)]")
    cycle_type = fields.Selection(related='program_id.cycle_type')
    cefr_code = fields.Selection([
        ('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')])
    credits_required = fields.Float()
    subject_ids = fields.Many2many('oski.school.subject', string='Subjects')
    company_id = fields.Many2one(related='program_id.company_id', store=True)

    _code_program_uniq = models.Constraint(
        'UNIQUE (program_id, code)', 'The level code must be unique inside a program.')

    @api.depends('sequence', 'program_id', 'manual_next_level',
                 'program_id.level_ids.sequence')
    def _compute_next_level(self):
        for level in self:
            if level.manual_next_level:
                continue
            following = level.program_id.level_ids.filtered(
                lambda l: l.id != level.id and (l.sequence, l.id) > (level.sequence, level.id)
            ).sorted(lambda l: (l.sequence, l.id))
            level.next_level_id = following[:1]
