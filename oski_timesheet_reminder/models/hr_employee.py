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
        if calendar and calendar.hours_per_week:
            return calendar.hours_per_week
        return company.oski_timesheet_expected_hours
