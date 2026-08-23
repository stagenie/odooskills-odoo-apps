from odoo import api, fields, models


class SchoolTeacher(models.Model):
    _name = 'oski.school.teacher'
    _description = 'Teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    name = fields.Char(related='partner_id.name', store=True, readonly=True)
    email = fields.Char(related='partner_id.email')
    phone = fields.Char(related='partner_id.phone')
    image_128 = fields.Image(related='partner_id.image_128')
    user_id = fields.Many2one('res.users', string='User', tracking=True,
                              help='Internal user given the Teacher group.')
    employee_code = fields.Char(size=16)
    subject_ids = fields.Many2many('oski.school.subject', string='Can teach')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _partner_uniq = models.Constraint('UNIQUE (partner_id)', 'This contact is already a teacher.')

    @api.model_create_multi
    def create(self, vals_list):
        teachers = super().create(vals_list)
        teachers._grant_teacher_group()
        return teachers

    def write(self, vals):
        res = super().write(vals)
        if 'user_id' in vals:
            self._grant_teacher_group()
        return res

    def _grant_teacher_group(self):
        group = self.env.ref('oski_school.group_school_teacher')
        users = self.mapped('user_id').filtered(lambda u: group not in u.group_ids)
        if users:
            users.sudo().write({'group_ids': [(4, group.id)]})
