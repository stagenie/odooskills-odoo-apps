from datetime import date, datetime, timedelta

import pytz

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAppointment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client RDV"})

    def _make_calendar(self):
        # Attendances 7j/7 9h–17h, tz UTC → calcul de créneaux déterministe.
        return self.env["resource.calendar"].create(
            {
                "name": "Dispo RDV",
                "tz": "UTC",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "j%s" % d,
                            "dayofweek": str(d),
                            "hour_from": 9.0,
                            "hour_to": 17.0,
                            "day_period": "morning",
                        }
                    )
                    for d in range(7)
                ],
            }
        )

    def _make_staff(self, n):
        users = self.env["res.users"]
        for i in range(n):
            users |= self.env["res.users"].create(
                {"name": "Staff %s" % i, "login": "staff_rdv_%s" % i}
            )
        return users

    def _make_type(self, duration=1.0, n_staff=2, **kw):
        vals = {
            "name": "Consultation",
            "duration": duration,
            "resource_calendar_id": self._make_calendar().id,
            "staff_user_ids": [Command.set(self._make_staff(n_staff).ids)],
        }
        vals.update(kw)
        return self.env["appointment.type"].create(vals)

    def _future_date(self, days=7):
        return date.today() + timedelta(days=days)

    def _get_first_slot(self, t, d):
        slots = t._get_available_slots(d, d)
        self.assertTrue(slots, "aucun créneau pour tester")
        return slots[0][0]

    # ---- Task 1 : type ----
    def test_type_create(self):
        t = self._make_type()
        self.assertEqual(t.duration, 1.0)
        self.assertEqual(len(t.staff_user_ids), 2)
        self.assertEqual(t.appointment_count, 0)

    def test_duration_constraint(self):
        with self.assertRaises(ValidationError):
            self._make_type(duration=0.0)

    # ---- Task 2 : moteur ----
    def test_slots_within_hours(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        slots = t._get_available_slots(d, d)
        self.assertTrue(slots)
        for slot_start, _free in slots:
            self.assertGreaterEqual(slot_start.hour, 9)
            self.assertLess(slot_start.hour, 17)

    def test_slot_duration(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        starts = [s[0] for s in t._get_available_slots(d, d)]
        self.assertTrue(all(s.minute == 0 for s in starts))
        hours = sorted(s.hour for s in starts)
        self.assertEqual(hours, list(range(9, 17)))

    def test_slot_excludes_busy_staff(self):
        t = self._make_type(duration=1.0, n_staff=1)
        staff = t.staff_user_ids
        d = self._future_date(7)
        busy_start = datetime(d.year, d.month, d.day, 10, 0, 0)
        self.env["calendar.event"].create(
            {
                "name": "Occupé",
                "start": busy_start,
                "stop": busy_start + timedelta(hours=1),
                "user_id": staff.id,
                "partner_ids": [Command.set(staff.partner_id.ids)],
            }
        )
        starts = [s[0].hour for s in t._get_available_slots(d, d)]
        self.assertNotIn(10, starts)
        self.assertIn(9, starts)

    def test_min_notice(self):
        t = self._make_type(duration=1.0, n_staff=1, min_notice_hours=24 * 365)
        d = self._future_date(7)
        self.assertEqual(t._get_available_slots(d, d), [])

    def test_max_days_ahead(self):
        t = self._make_type(duration=1.0, n_staff=1, max_days_ahead=1)
        d = self._future_date(10)
        self.assertEqual(t._get_available_slots(d, d), [])

    # ---- Task 3 : booking ----
    def _book(self, t, slot_start, staff=None):
        wiz = self.env["appointment.booking.wizard"].create(
            {
                "appointment_type_id": t.id,
                "partner_id": self.partner.id,
                "slot_start": slot_start,
                "staff_user_id": (staff or t.staff_user_ids[0]).id,
            }
        )
        wiz.action_confirm()
        return self.env["calendar.event"].search(
            [("appointment_type_id", "=", t.id)], order="create_date desc", limit=1
        )

    def test_wizard_creates_event(self):
        t = self._make_type(duration=1.0, n_staff=1)
        t.reminder_ids = [
            Command.create(
                {"name": "R24h", "alarm_type": "notification", "duration": 1, "interval": "days"}
            )
        ]
        d = self._future_date(7)
        slot = self._get_first_slot(t, d)
        event = self._book(t, slot)
        self.assertEqual(event.appointment_type_id, t)
        self.assertEqual(event.appointment_state, "booked")
        self.assertEqual(event.user_id, t.staff_user_ids[0])
        self.assertIn(self.partner, event.partner_ids)
        self.assertEqual(event.alarm_ids, t.reminder_ids)

    def test_confirmation_email(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        slot = self._get_first_slot(t, d)
        event = self._book(t, slot)
        mails = self.env["mail.mail"].search(
            [("model", "=", "calendar.event"), ("res_id", "=", event.id)]
        )
        self.assertTrue(mails)

    def test_cancel_frees_slot(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        slot = self._get_first_slot(t, d)
        event = self._book(t, slot)
        self.assertNotIn(slot.hour, [s[0].hour for s in t._get_available_slots(d, d)])
        event.appointment_state = "cancelled"
        self.assertIn(slot.hour, [s[0].hour for s in t._get_available_slots(d, d)])
