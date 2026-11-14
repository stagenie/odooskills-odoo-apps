from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    appointment_type_id = fields.Many2one(
        "appointment.type", string="Appointment Type", index=True
    )
    appointment_partner_id = fields.Many2one(
        "res.partner", string="Appointment Customer", index=True,
        help="Customer who booked the appointment (recipient of the confirmation).",
    )
    appointment_tz = fields.Char(
        string="Customer Time Zone",
        help="Time zone in which the customer chose the time slot (dates shown in emails).",
    )
    appointment_state = fields.Selection(
        [
            ("booked", "Booked"),
            ("done", "Attended"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        string="Appointment Status",
    )
