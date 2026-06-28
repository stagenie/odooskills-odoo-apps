from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    appointment_type_id = fields.Many2one(
        "appointment.type", string="Type de RDV", index=True
    )
    appointment_state = fields.Selection(
        [
            ("booked", "Réservé"),
            ("done", "Honoré"),
            ("cancelled", "Annulé"),
            ("no_show", "Absent"),
        ],
        string="État du RDV",
    )
