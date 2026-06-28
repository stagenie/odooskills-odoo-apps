from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AppointmentType(models.Model):
    _name = "appointment.type"
    _description = "Type de rendez-vous"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    duration = fields.Float(string="Durée (heures)", required=True, default=1.0)
    resource_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Disponibilité",
        required=True,
        default=lambda self: self.env.company.resource_calendar_id,
    )
    staff_user_ids = fields.Many2many(
        "res.users", string="Personnel", required=True
    )
    min_notice_hours = fields.Float(string="Préavis minimum (heures)", default=1.0)
    max_days_ahead = fields.Integer(string="Horizon (jours)", default=30)
    reminder_ids = fields.Many2many("calendar.alarm", string="Rappels")
    location = fields.Char(string="Lieu")
    description = fields.Html(string="Description")
    appointment_count = fields.Integer(
        string="Rendez-vous", compute="_compute_appointment_count"
    )
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)

    def _compute_appointment_count(self):
        Event = self.env["calendar.event"]
        for atype in self:
            atype.appointment_count = (
                Event.search_count([("appointment_type_id", "=", atype.id)])
                if atype.id
                else 0
            )

    @api.constrains("duration")
    def _check_duration(self):
        for atype in self:
            if atype.duration <= 0:
                raise ValidationError("La durée doit être strictement positive.")

    def _slot_free_staff(self, slot_start_utc, slot_stop_utc):
        """res.users du staff libres sur [slot_start, slot_stop[ (UTC naïf)."""
        self.ensure_one()
        domain = [
            ("start", "<", slot_stop_utc),
            ("stop", ">", slot_start_utc),
            ("appointment_state", "!=", "cancelled"),
            "|",
            ("user_id", "in", self.staff_user_ids.ids),
            ("partner_ids", "in", self.staff_user_ids.partner_id.ids),
        ]
        busy = self.env["calendar.event"].search(domain)
        busy_user_ids = set(busy.user_id.ids) | set(
            busy.partner_ids.mapped("user_ids").ids
        )
        return self.staff_user_ids.filtered(lambda u: u.id not in busy_user_ids)

    def _get_available_slots(self, date_from, date_to):
        """Créneaux libres : [(start_utc_naive, [staff_user_ids]), ...]."""
        self.ensure_one()
        cal = self.resource_calendar_id
        tz = pytz.timezone(cal.tz or "UTC")
        start = tz.localize(datetime.combine(date_from, time.min))
        end = tz.localize(datetime.combine(date_to, time.max))
        intervals = cal._work_intervals_batch(start, end, resources=None, tz=tz)[False]
        delta = timedelta(hours=self.duration)
        now_utc = datetime.utcnow()
        notice = now_utc + timedelta(hours=self.min_notice_hours)
        horizon = now_utc + timedelta(days=self.max_days_ahead)
        result = []
        for iv_start, iv_stop, _meta in intervals:
            slot = iv_start
            while slot + delta <= iv_stop:
                slot_start_utc = slot.astimezone(pytz.utc).replace(tzinfo=None)
                slot_stop_utc = slot_start_utc + delta
                if notice <= slot_start_utc <= horizon:
                    free = self._slot_free_staff(slot_start_utc, slot_stop_utc)
                    if free:
                        result.append((slot_start_utc, free.ids))
                slot += delta
        return sorted(result, key=lambda r: r[0])
