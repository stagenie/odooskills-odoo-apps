from datetime import timedelta

from odoo import Command, fields, models
from odoo.exceptions import UserError


class AppointmentBookingWizard(models.TransientModel):
    _name = "appointment.booking.wizard"
    _description = "Prise de rendez-vous"

    appointment_type_id = fields.Many2one(
        "appointment.type", string="Type de RDV", required=True
    )
    partner_id = fields.Many2one("res.partner", string="Client", required=True)
    slot_start = fields.Datetime(string="Créneau", required=True)
    staff_user_id = fields.Many2one("res.users", string="Avec")

    def action_confirm(self):
        self.ensure_one()
        atype = self.appointment_type_id
        delta = timedelta(hours=atype.duration)
        slot_stop = self.slot_start + delta
        staff = self.staff_user_id or atype.staff_user_ids[:1]
        free = atype._slot_free_staff(self.slot_start, slot_stop)
        if staff not in free:
            raise UserError("Ce créneau n'est plus disponible.")
        event = self.env["calendar.event"].create(
            {
                "name": "%s - %s" % (atype.name, self.partner_id.name),
                "start": self.slot_start,
                "stop": slot_stop,
                "user_id": staff.id,
                "partner_ids": [
                    Command.set((self.partner_id | staff.partner_id).ids)
                ],
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
