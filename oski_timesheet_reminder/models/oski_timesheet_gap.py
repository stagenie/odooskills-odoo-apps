from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models


class OskiTimesheetGap(models.Model):
    """Un retard de saisie, semaine par semaine et employé par employé.

    Le retard est une donnée, pas un courriel : il se relit, se totalise et se
    compare d'une semaine à l'autre. Le rappel n'en est qu'une conséquence.
    """

    _name = "oski.timesheet.gap"
    _description = "Retard de saisie des temps"
    _order = "date_from desc, employee_id"
    _rec_name = "employee_id"

    employee_id = fields.Many2one(
        "hr.employee", string="Employé", required=True, ondelete="cascade",
        index=True)
    user_id = fields.Many2one(
        "res.users", string="Utilisateur", related="employee_id.user_id",
        store=True, readonly=True)
    date_from = fields.Date(string="Du", required=True, index=True)
    date_to = fields.Date(string="Au", required=True)
    expected_hours = fields.Float(string="Attendu", digits=(6, 2))
    logged_hours = fields.Float(string="Saisi", digits=(6, 2))
    missing_hours = fields.Float(
        string="Manquant", digits=(6, 2), compute="_compute_missing",
        store=True)
    reminded_on = fields.Datetime(string="Rappelé le", readonly=True)
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company)

    _unique_week = models.Constraint(
        "UNIQUE(employee_id, date_from)",
        "Ce retard est déjà consigné pour cette semaine.")

    @api.depends("expected_hours", "logged_hours")
    def _compute_missing(self):
        for gap in self:
            gap.missing_hours = max(gap.expected_hours - gap.logged_hours, 0.0)

    # -- Tâche planifiée --------------------------------------------------

    @api.model
    def _oski_cron_check_last_week(self):
        today = fields.Date.context_today(self)
        # La semaine écoulée, du lundi au dimanche : relever la semaine en
        # cours accuserait tout le monde d'un retard qui n'existe pas encore.
        last_monday = today - timedelta(days=today.weekday() + 7)
        return self._oski_check_week(last_monday)

    @api.model
    def _oski_check_week(self, monday):
        sunday = monday + timedelta(days=6)
        gaps = self.browse()
        for company in self.env["res.company"].search([
                ("oski_timesheet_reminder_active", "=", True)]):
            gaps |= self._oski_check_company_week(company, monday, sunday)
        return gaps

    @api.model
    def _oski_check_company_week(self, company, monday, sunday):
        employees = self.env["hr.employee"].sudo().search([
            ("company_id", "=", company.id),
            ("user_id", "!=", False),
        ])
        if not employees:
            return self.browse()
        logged = dict(self.env["account.analytic.line"].sudo()._read_group(
            [("employee_id", "in", employees.ids),
             ("project_id", "!=", False),
             ("date", ">=", monday), ("date", "<=", sunday)],
            ["employee_id"], ["unit_amount:sum"]))
        gaps = self.browse()
        for employee in employees:
            expected = employee._oski_expected_hours(company)
            done = logged.get(employee, 0.0)
            if expected - done <= company.oski_timesheet_tolerance:
                continue
            gaps |= self._oski_record(employee, monday, sunday, expected, done)
        return gaps

    @api.model
    def _oski_record(self, employee, monday, sunday, expected, done):
        gap = self.sudo().search([
            ("employee_id", "=", employee.id), ("date_from", "=", monday)],
            limit=1)
        values = {
            "expected_hours": expected,
            "logged_hours": done,
        }
        if gap:
            gap.write(values)
        else:
            gap = self.sudo().create(dict(values, **{
                "employee_id": employee.id,
                "date_from": monday,
                "date_to": sunday,
                "company_id": employee.company_id.id,
            }))
        gap._oski_remind()
        return gap

    def _oski_remind(self):
        """Une activité sur la fiche employé, jamais un courriel.

        Le rappel se pose une seule fois par semaine relevée : repasser la
        tâche planifiée ne doit pas empiler les rappels.
        """
        self.ensure_one()
        if self.reminded_on or not self.employee_id.user_id:
            return False
        activity = self.env["mail.activity"].sudo().with_context(
            mail_activity_quick_update=True).create({
                "res_model_id": self.env["ir.model"]._get_id("hr.employee"),
                "res_id": self.employee_id.id,
                "activity_type_id": self.env.ref(
                    "mail.mail_activity_data_todo").id,
                "user_id": self.employee_id.user_id.id,
                "date_deadline": fields.Date.context_today(self),
                "summary": _("Feuille de temps incomplète"),
                "note": Markup("<p>%s</p>") % _(
                    "Semaine du %(from)s au %(to)s : %(logged)s h saisies sur "
                    "%(expected)s h attendues.",
                    **{"from": self.date_from, "to": self.date_to,
                       "logged": round(self.logged_hours, 2),
                       "expected": round(self.expected_hours, 2)}),
            })
        self.sudo().reminded_on = fields.Datetime.now()
        return activity
