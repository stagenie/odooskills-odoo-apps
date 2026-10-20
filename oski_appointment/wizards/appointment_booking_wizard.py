from datetime import timedelta

from odoo import Command, fields, models


class AppointmentBookingWizard(models.TransientModel):
    _name = "appointment.booking.wizard"
    _description = "Prise de rendez-vous"

    appointment_type_id = fields.Many2one(
        "appointment.type", string="Type de RDV", required=True
    )
    staff_user_ids = fields.Many2many(related="appointment_type_id.staff_user_ids")
    partner_id = fields.Many2one("res.partner", string="Client", required=True)
    slot_start = fields.Datetime(string="Créneau", required=True)
    staff_user_id = fields.Many2one(
        "res.users", string="Avec",
        help="Laisser vide : le premier membre du personnel libre est retenu.",
    )

    def action_confirm(self):
        self.ensure_one()
        atype = self.appointment_type_id
        staff = atype._check_slot_bookable(self.slot_start, self.staff_user_id)
        slot_stop = self.slot_start + timedelta(hours=atype.duration)
        event = self.env["calendar.event"].create(
            {
                "name": "%s - %s" % (atype.name, self.partner_id.name),
                "start": self.slot_start,
                "stop": slot_stop,
                "user_id": staff.id,
                "partner_ids": [
                    Command.set((self.partner_id | staff.partner_id).ids)
                ],
                "appointment_partner_id": self.partner_id.id,
                "appointment_type_id": atype.id,
                "appointment_state": "booked",
                "alarm_ids": [Command.set(atype.reminder_ids.ids)],
                "location": atype.location or False,
            }
        )
        template = self.env.ref(
            "oski_appointment.mail_template_appointment_confirmation",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(event.id, force_send=False)
        return {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "res_id": event.id,
            "view_mode": "form",
        }
