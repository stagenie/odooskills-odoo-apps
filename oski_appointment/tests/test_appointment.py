from datetime import date, datetime, timedelta

import psycopg2.errors

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestAppointment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client RDV"})

    def _make_calendar(self):
        # Attendances 7j/7 9h–17h ; le fuseau (UTC) est porté par le type
        # (Odoo 20 : plus de fuseau sur resource.calendar).
        return self.env["resource.calendar"].create(
            {
                "name": "Dispo RDV",
                "attendance_ids": [Command.clear()] + [
                    Command.create(
                        {"dayofweek": str(d), "hour_from": 9.0, "hour_to": 17.0}
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
            "tz": "UTC",
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

    def test_tz_defaults_to_calendar_company(self):
        # Odoo 20 : le fuseau vient de la société du calendrier (resource.calendar.tz supprimé)
        company = self.env["res.company"].create({"name": "Société Tokyo RDV", "tz": "Asia/Tokyo"})
        cal = self._make_calendar()
        cal.company_id = company
        t = self.env["appointment.type"].create({
            "name": "Fuseau", "resource_calendar_id": cal.id,
            "staff_user_ids": [Command.set(self._make_staff(1).ids)],
        })
        self.assertEqual(t.tz, "Asia/Tokyo")
        d = self._future_date(7)
        starts = sorted(s[0] for s in t._get_available_slots(d, d))
        self.assertEqual(starts[0], datetime(d.year, d.month, d.day, 0, 0))  # 9h Tokyo = 0h UTC

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

    # ---- Contrôles de réservation (lot A24) ----
    def test_past_slot_refused(self):
        t = self._make_type(duration=1.0, n_staff=1)
        y = date.today() - timedelta(days=1)
        with self.assertRaises(UserError):
            self._book(t, datetime(y.year, y.month, y.day, 10, 0, 0))

    def test_out_of_hours_slot_refused(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        with self.assertRaises(UserError):
            self._book(t, datetime(d.year, d.month, d.day, 3, 0, 0))

    def test_misaligned_slot_refused(self):
        t = self._make_type(duration=1.0, n_staff=1)
        d = self._future_date(7)
        with self.assertRaises(UserError):
            self._book(t, datetime(d.year, d.month, d.day, 10, 30, 0))

    def test_archived_type_refused(self):
        t = self._make_type(duration=1.0, n_staff=1)
        slot = self._get_first_slot(t, self._future_date(7))
        t.active = False
        with self.assertRaises(UserError):
            self._book(t, slot)

    def test_staff_outside_type_refused(self):
        t = self._make_type(duration=1.0, n_staff=1)
        slot = self._get_first_slot(t, self._future_date(7))
        intruder = self.env["res.users"].create({"name": "Hors", "login": "hors_rdv"})
        with self.assertRaises(UserError):
            self._book(t, slot, staff=intruder)

    def test_no_staff_picks_first_free(self):
        t = self._make_type(duration=1.0, n_staff=2)
        slot = self._get_first_slot(t, self._future_date(7))
        busy = t.staff_user_ids[0]
        self.env["calendar.event"].create({
            "name": "Occupé", "start": slot, "stop": slot + timedelta(hours=1),
            "user_id": busy.id, "partner_ids": [Command.set(busy.partner_id.ids)],
        })
        wiz = self.env["appointment.booking.wizard"].create({
            "appointment_type_id": t.id, "partner_id": self.partner.id,
            "slot_start": slot,
        })
        wiz.action_confirm()
        event = self.env["calendar.event"].search([("appointment_type_id", "=", t.id)])
        self.assertEqual(event.user_id, t.staff_user_ids[1])

    def test_confirmation_goes_to_client_not_staff(self):
        # partner_ids est trié par nom : "Aaa" (personnel) passe avant "Zzz" (client)
        staff = self.env["res.users"].create({
            "name": "Aaa Personnel", "login": "aaa_rdv", "email": "staff@example.com",
        })
        client = self.env["res.partner"].create({"name": "Zzz Client", "email": "client@example.com"})
        t = self._make_type(duration=1.0, n_staff=0, staff_user_ids=[Command.set(staff.ids)])
        slot = self._get_first_slot(t, self._future_date(7))
        self.env["appointment.booking.wizard"].create({
            "appointment_type_id": t.id, "partner_id": client.id, "slot_start": slot,
        }).action_confirm()
        event = self.env["calendar.event"].search([("appointment_type_id", "=", t.id)])
        self.assertEqual(event.appointment_partner_id, client)
        mail = self.env["mail.mail"].search([
            ("model", "=", "calendar.event"), ("res_id", "=", event.id),
            ("subject", "like", "Confirmation de votre rendez-vous"),
        ])
        self.assertEqual(len(mail), 1)
        # le modèle convertit l'adresse connue en destinataire partenaire
        recipients = (mail.email_to or "") + " ".join(mail.recipient_ids.mapped("email"))
        self.assertIn("client@example.com", recipients)
        self.assertNotIn("staff@example.com", recipients)

    def test_confirmation_date_in_calendar_timezone(self):
        t = self._make_type(duration=1.0, n_staff=1)
        t.tz = "Africa/Algiers"  # UTC+1, sans heure d'été
        slot = self._get_first_slot(t, self._future_date(7))  # 9h locale = 8h UTC
        self.assertEqual(slot.hour, 8)
        event = self._book(t, slot)
        mail = self.env["mail.mail"].search([
            ("model", "=", "calendar.event"), ("res_id", "=", event.id),
            ("subject", "like", "Confirmation de votre rendez-vous"),
        ])
        self.assertIn("09:00", str(mail.body_html))
        self.assertNotIn("08:00", str(mail.body_html))

    def test_confirmation_date_in_client_timezone(self):
        t = self._make_type(duration=1.0, n_staff=1)  # calendrier en UTC
        slot = self._get_first_slot(t, self._future_date(7))  # 9h UTC
        event = self._book(t, slot)
        event.appointment_tz = "Asia/Tokyo"  # UTC+9 toute l'année
        template = self.env.ref("oski_appointment.mail_template_appointment_confirmation")
        body = str(template._render_field("body_html", event.ids)[event.id])
        self.assertIn("18:00", body)
        self.assertIn("Asia/Tokyo", body)

    def test_type_multi_company_rule(self):
        other = self.env["res.company"].create({"name": "Autre société RDV"})
        t = self._make_type(duration=1.0, n_staff=1)
        user_b = self.env["res.users"].create({
            "name": "Agent B", "login": "agent_b_rdv",
            "company_id": other.id, "company_ids": [Command.set(other.ids)],
            "group_ids": [Command.set(self.env.ref("oski_appointment.group_appointment_user").ids)],
        })
        types_b = self.env["appointment.type"].with_user(user_b).search([("id", "=", t.id)])
        self.assertFalse(types_b)
        types_main = self.env["appointment.type"].search([("id", "=", t.id)])
        self.assertEqual(types_main, t)


class TestAppointmentConcurrency(TransactionCase):
    """Deux réservations simultanées du même créneau : une seule aboutit.

    Transactions réelles (curseurs distincts, données validées puis nettoyées) :
    c'est le seul moyen de reproduire le double clic / deux visiteurs.
    """

    def test_concurrent_booking_same_slot(self):
        registry = self.registry
        with registry.cursor() as cr0:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            cal = env0["resource.calendar"].create({
                "name": "Concurrence RDV",
                "attendance_ids": [Command.clear()] + [
                    Command.create({"dayofweek": str(d), "hour_from": 9.0, "hour_to": 17.0})
                    for d in range(7)
                ],
            })
            staff = env0["res.users"].create({"name": "Seul", "login": "seul_rdv_concur"})
            partners = env0["res.partner"].create([{"name": "Visiteur 1"}, {"name": "Visiteur 2"}])
            atype = env0["appointment.type"].create({
                "name": "Concurrence", "duration": 1.0,
                "resource_calendar_id": cal.id, "tz": "UTC",
                "staff_user_ids": [Command.set(staff.ids)],
            })
            ids = (cal.id, staff.id, partners.ids, atype.id)
        cal_id, staff_id, partner_ids, type_id = ids
        d = date.today() + timedelta(days=7)
        cr1, cr2 = registry.cursor(), registry.cursor()
        try:
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            env2 = api.Environment(cr2, SUPERUSER_ID, {})
            slot = env1["appointment.type"].browse(type_id)._get_available_slots(d, d)[0][0]
            # le second visiteur voit le créneau libre (instantané pris maintenant)
            self.assertTrue(env2["appointment.type"].browse(type_id)._get_available_slots(d, d))

            def book(env, partner_id):
                env["appointment.booking.wizard"].create({
                    "appointment_type_id": type_id, "partner_id": partner_id,
                    "slot_start": slot,
                }).action_confirm()
                env.flush_all()

            book(env1, partner_ids[0])
            cr1.commit()
            with self.assertRaises(psycopg2.errors.SerializationFailure), \
                    mute_logger("odoo.sql_db"):
                book(env2, partner_ids[1])
        finally:
            cr1.rollback()
            cr2.rollback()
            cr1.close()
            cr2.close()
            with registry.cursor() as cr3:
                env3 = api.Environment(cr3, SUPERUSER_ID, {})
                events = env3["calendar.event"].search([("appointment_type_id", "=", type_id)])
                env3["mail.mail"].search(
                    [("model", "=", "calendar.event"), ("res_id", "in", events.ids)]
                ).unlink()
                events.unlink()
                env3["appointment.type"].browse(type_id).unlink()
                env3["resource.calendar"].browse(cal_id).unlink()
                env3["res.users"].browse(staff_id).active = False
