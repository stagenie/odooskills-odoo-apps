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
        tracking=True,
    )

    def _set_appointment_state(self, state):
        # seuls les rendez-vous (pas les réunions ordinaires) changent d'état
        self.filtered("appointment_type_id").write({"appointment_state": state})
        return True

    def action_appointment_done(self):
        return self._set_appointment_state("done")

    def action_appointment_no_show(self):
        return self._set_appointment_state("no_show")

    def action_appointment_cancel(self):
        return self._set_appointment_state("cancelled")
