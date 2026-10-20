import re
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


def _bump_years(text, years=1):
    """'2026-2027' → '2027-2028', '26-27' → '27-28'. Laisse le reste intact."""
    def repl(m):
        n = m.group(0)
        return str(int(n) + years).zfill(len(n))
    return re.sub(r'\d{2,4}', repl, text or '')


class StructureDuplicateWizard(models.TransientModel):
    _name = 'oski.school.structure.duplicate.wizard'
    _description = 'Duplicate the structure into a new period'

    period_id = fields.Many2one('oski.school.period', required=True)
    name = fields.Char(compute='_compute_defaults', store=True, readonly=False, required=True, precompute=True)
    code = fields.Char(compute='_compute_defaults', store=True, readonly=False, required=True, precompute=True)
    date_start = fields.Date(compute='_compute_defaults', store=True, readonly=False, required=True, precompute=True)
    date_end = fields.Date(compute='_compute_defaults', store=True, readonly=False, required=True, precompute=True)
    copy_terms = fields.Boolean(default=True)
    copy_classes = fields.Boolean(default=True)

    @api.depends('period_id')
    def _compute_defaults(self):
        for wiz in self:
            src = wiz.period_id
            if not src:
                continue
            if src.period_type == 'year':
                shift = relativedelta(years=1)
                wiz.date_start = src.date_start + shift
                wiz.date_end = src.date_end + shift
                wiz.name = _bump_years(src.name)
                wiz.code = _bump_years(src.code)
            elif src.period_type == 'semester':
                shift = relativedelta(months=6)
                wiz.date_start = src.date_start + shift
                wiz.date_end = src.date_end + shift
                wiz.name = f'{src.name} +1'
                wiz.code = f'{src.code}+'
            else:
                duration = (src.date_end - src.date_start).days
                wiz.date_start = src.date_end + timedelta(days=1)
                wiz.date_end = wiz.date_start + timedelta(days=duration)
                wiz.name = f'{src.name} +1'
                wiz.code = f'{src.code}+'

    def action_duplicate(self):
        self.ensure_one()
        src = self.period_id
        shift = self.date_start - src.date_start
        new = self.env['oski.school.period'].create({
            'name': self.name, 'code': self.code, 'period_type': src.period_type,
            'date_start': self.date_start, 'date_end': self.date_end,
            'company_id': src.company_id.id,
        })
        if self.copy_terms:
            self.env['oski.school.term'].create([{
                'period_id': new.id, 'name': t.name, 'sequence': t.sequence,
                'date_start': min(t.date_start + shift, new.date_end),
                'date_end': min(t.date_end + shift, new.date_end),
            } for t in src.term_ids])
        if self.copy_classes:
            classes = self.env['oski.school.class'].search([('period_id', '=', src.id)])
            self.env['oski.school.class'].create([{
                'level_id': c.level_id.id, 'period_id': new.id, 'suffix': c.suffix,
                'room_id': c.room_id.id, 'homeroom_teacher_id': c.homeroom_teacher_id.id,
                'capacity': c.capacity, 'company_id': c.company_id.id, 'state': 'open',
                'subject_line_ids': [(0, 0, {
                    'subject_id': l.subject_id.id, 'teacher_id': l.teacher_id.id,
                    'coefficient': l.coefficient}) for l in c.subject_line_ids],
            } for c in classes])
        return {
            'type': 'ir.actions.act_window', 'res_model': 'oski.school.period',
            'res_id': new.id, 'view_mode': 'form', 'target': 'current',
        }
