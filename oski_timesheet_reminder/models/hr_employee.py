from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _oski_expected_hours(self, company):
        """L'horaire de l'employé fait foi ; la société n'est qu'un recours.

        Un mi-temps relevé sur 35 heures serait en retard toutes les semaines,
        et le tableau ne dirait plus rien à personne.
        """
        self.ensure_one()
        calendar = self.resource_calendar_id or company.resource_calendar_id
        hours = self._oski_calendar_week_hours(calendar)
        if hours:
            return hours
        return company.oski_timesheet_expected_hours

    @staticmethod
    def _oski_calendar_week_hours(calendar):
        """Heures d'une semaine de l'horaire de travail.

        En v18, ``resource.calendar`` n'a pas de champ ``hours_per_week``
        (apparu en v19) : on fait la somme des créneaux, pause déjeuner
        exclue, divisée par deux pour un horaire sur deux semaines. Un horaire
        flexible n'a pas de créneaux : son temps plein fait foi.
        """
        if not calendar:
            return 0.0
        if calendar.flexible_hours:
            return calendar.full_time_required_hours
        hours = sum(calendar._get_global_attendances().mapped("duration_hours"))
        return hours / 2 if calendar.two_weeks_calendar else hours
