from datetime import timedelta
from odoo import fields, models
from odoo.exceptions import ValidationError


class TermGenerateWizard(models.TransientModel):
    _name = 'oski.school.term.generate.wizard'
    _description = 'Generate Terms'

    period_id = fields.Many2one('oski.school.period', required=True)
    count = fields.Integer(default=3, required=True)
    label = fields.Char(default='Term', required=True)

    def action_generate(self):
        self.ensure_one()
        if self.period_id.term_ids:
            raise ValidationError(self.env._('This period already has terms.'))
        if self.count < 1:
            raise ValidationError(self.env._('The number of terms must be at least 1.'))
        total_days = (self.period_id.date_end - self.period_id.date_start).days + 1
        chunk, rest = divmod(total_days, self.count)
        start = self.period_id.date_start
        vals = []
        for i in range(self.count):
            days = chunk + (1 if i < rest else 0)
            end = start + timedelta(days=days - 1)
            vals.append({
                'period_id': self.period_id.id, 'sequence': i + 1,
                'name': f'{self.label} {i + 1}', 'date_start': start, 'date_end': end,
            })
            start = end + timedelta(days=1)
        self.env['oski.school.term'].create(vals)
        return {'type': 'ir.actions.act_window_close'}
