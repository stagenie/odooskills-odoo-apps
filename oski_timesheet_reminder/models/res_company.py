from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_timesheet_reminder_active = fields.Boolean(
        string="Timesheet Entry Reminder", default=False)
    oski_timesheet_expected_hours = fields.Float(
        string="Expected Hours per Week", default=35.0,
        help="Used for employees whose working schedule says nothing. "
             "Otherwise, the employee's working schedule prevails.")
    oski_timesheet_tolerance = fields.Float(
        string="Tolerance (Hours)", default=1.0,
        help="Below this gap, the employee is not disturbed.")
