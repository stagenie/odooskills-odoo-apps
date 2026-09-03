from datetime import date, timedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTimesheetReminder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            "oski_timesheet_reminder_active": True,
            "oski_timesheet_expected_hours": 35.0,
            "oski_timesheet_tolerance": 1.0,
        })
        cls.user = cls.env["res.users"].create({
            "name": "Salarié", "login": "oski_timesheet_salarie",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])]})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Salarié", "user_id": cls.user.id,
            "company_id": cls.company.id})
        cls.project = cls.env["project.project"].create({
            "name": "Chantier", "allow_timesheets": True,
            "company_id": cls.company.id})
        # Une semaine pleine et close, jamais la semaine en cours.
        cls.monday = date(2026, 8, 3)
        cls.gaps = cls.env["oski.timesheet.gap"]
        # L'attendu vient de l'horaire de travail de l'employé, hérité de la
        # société : le figer à 35 dans les tests reviendrait à éprouver la
        # valeur par défaut d'Odoo plutôt que la règle du module.
        cls.expected = cls.employee._oski_expected_hours(cls.company)

    def _log(self, hours, day_offset=0):
        return self.env["account.analytic.line"].create({
            "name": "Travaux",
            "project_id": self.project.id,
            "employee_id": self.employee.id,
            "date": self.monday + timedelta(days=day_offset),
            "unit_amount": hours,
        })

    def _run(self):
        """Le relevé porte sur TOUS les employés de la société — celui du
        compte administrateur compris, qui ne saisit jamais rien. La suite ne
        regarde donc que le sien."""
        gaps = self.gaps._oski_check_week(self.monday)
        return gaps.filtered(lambda gap: gap.employee_id == self.employee)

    def _activities(self):
        return self.env["mail.activity"].search([
            ("res_model", "=", "hr.employee"),
            ("res_id", "=", self.employee.id)])

    # -- Le relevé --------------------------------------------------------

    def test_an_empty_week_is_a_full_gap(self):
        gap = self._run()
        self.assertEqual(len(gap), 1)
        self.assertEqual(gap.employee_id, self.employee)
        self.assertEqual(gap.expected_hours, self.expected)
        self.assertEqual(gap.logged_hours, 0.0)
        self.assertEqual(gap.missing_hours, self.expected)
        self.assertEqual(gap.date_from, self.monday)
        self.assertEqual(gap.date_to, self.monday + timedelta(days=6))

    def test_the_hours_of_the_week_are_summed(self):
        self._log(7.0)
        self._log(7.0, 1)
        self._log(7.0, 2)
        gap = self._run()
        self.assertEqual(gap.logged_hours, 21.0)
        self.assertEqual(gap.missing_hours, self.expected - 21.0)

    def test_a_full_week_raises_nothing(self):
        self._log(self.expected)
        self.assertFalse(self._run())

    def test_the_tolerance_spares_the_quarter_hour(self):
        self._log(self.expected - 0.5)
        self.assertFalse(self._run())
        self._log(-2.0)
        self.assertTrue(self._run())

    def test_the_company_setting_is_the_last_resort(self):
        """Sans horaire de travail — ni sur l'employé, ni sur la société — il
        reste le chiffre saisi dans les paramètres."""
        self.company.resource_calendar_id = False
        self.employee.resource_calendar_id = False
        self.company.oski_timesheet_expected_hours = 28.0
        self.assertEqual(self.employee._oski_expected_hours(self.company), 28.0)
        gap = self._run()
        self.assertEqual(gap.expected_hours, 28.0)

    def test_hours_outside_the_week_do_not_count(self):
        self._log(self.expected, day_offset=-1)
        self._log(self.expected, day_offset=7)
        gap = self._run()
        self.assertEqual(gap.logged_hours, 0.0)

    def test_a_part_time_is_judged_on_its_own_schedule(self):
        """Un mi-temps relevé sur 35 heures serait en retard toutes les
        semaines, et le tableau ne dirait plus rien à personne."""
        calendar = self.env["resource.calendar"].create({
            "name": "Mi-temps", "hours_per_day": 3.5,
            "attendance_ids": [(5, 0, 0)] + [
                (0, 0, {"name": "Jour %s" % index, "dayofweek": str(index),
                        "hour_from": 9.0, "hour_to": 12.5})
                for index in range(5)],
        })
        self.employee.resource_calendar_id = calendar
        self._log(17.5)
        self.assertFalse(self._run())

    def test_an_employee_without_a_user_is_left_out(self):
        self.employee.user_id = False
        self.assertFalse(self._run())

    def test_nothing_happens_when_the_company_says_no(self):
        self.company.oski_timesheet_reminder_active = False
        self.assertFalse(self._run())

    def test_running_twice_updates_the_same_line(self):
        self._run()
        self._log(10.0)
        gaps = self._run()
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps.logged_hours, 10.0)
        self.assertEqual(len(self.gaps.search([
            ("employee_id", "=", self.employee.id),
            ("date_from", "=", self.monday)])), 1)

    # -- Le rappel --------------------------------------------------------

    def test_the_employee_is_reminded_once(self):
        gap = self._run()
        self.assertTrue(gap.reminded_on)
        activity = self._activities()
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.user)
        self._run()
        self.assertEqual(len(self._activities()), 1)

    def test_the_reminder_is_an_activity_and_not_an_email(self):
        before = self.env["mail.mail"].search_count([])
        self._run()
        self.assertTrue(self._activities())
        self.assertEqual(self.env["mail.mail"].search_count([]), before)

    def test_the_reminder_says_what_is_missing(self):
        self._log(10.0)
        self._run()
        activity = self._activities()
        self.assertIn("10.0", activity.note)
        self.assertIn(str(round(self.expected, 2)), activity.note)

    # -- La semaine relevée -----------------------------------------------

    def test_every_employee_of_the_company_is_looked_at(self):
        """Le relevé ne se limite pas à qui a déjà saisi : c'est justement
        celui qui n'a rien saisi qu'il faut trouver."""
        other_user = self.env["res.users"].create({
            "name": "Autre", "login": "oski_timesheet_autre",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        other = self.env["hr.employee"].create({
            "name": "Autre", "user_id": other_user.id,
            "company_id": self.company.id})
        gaps = self.gaps._oski_check_week(self.monday)
        self.assertIn(other, gaps.employee_id)
        self.assertIn(self.employee, gaps.employee_id)

    def test_the_cron_looks_at_the_week_that_ended(self):
        """Relever la semaine en cours accuserait tout le monde d'un retard
        qui n'existe pas encore."""
        today = date.today()
        expected_monday = today - timedelta(days=today.weekday() + 7)
        gaps = self.gaps._oski_cron_check_last_week()
        gap = gaps.filtered(lambda one: one.employee_id == self.employee)
        self.assertTrue(gap)
        self.assertEqual(gap.date_from, expected_monday)
        self.assertLess(gap.date_to, today)

    # -- Pourquoi ce module existe ----------------------------------------

    def test_the_core_reminder_switch_forgets_itself(self):
        """Community affiche deux cases « Reminder » qui ne sont reliées à
        rien : aucune tâche planifiée, aucun modèle de courriel, et la valeur
        n'est même pas conservée. Si Odoo les branche un jour, ce test tombera
        et il faudra revoir la raison d'être de ce module.
        """
        settings = self.env["res.config.settings"].create({})
        settings.reminder_user_allow = True
        settings.execute()
        self.assertFalse(
            self.env["res.config.settings"].create({}).reminder_user_allow,
            "le cœur conserve désormais ce réglage : revoir le positionnement")
        self.assertFalse(self.env["ir.cron"].search([
            ("code", "ilike", "reminder"),
            ("model_id.model", "=", "res.company"),
        ]).filtered(lambda cron: "timesheet" in (cron.name or "").lower()))
