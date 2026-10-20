from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    appointment_type_id = fields.Many2one(
        "appointment.type", string="Type de RDV", index=True
    )
    appointment_partner_id = fields.Many2one(
        "res.partner", string="Client du RDV", index=True,
        help="Client qui a pris le rendez-vous (destinataire de la confirmation).",
    )
    appointment_tz = fields.Char(
        string="Fuseau du client",
        help="Fuseau dans lequel le client a choisi son créneau (dates des courriels).",
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
