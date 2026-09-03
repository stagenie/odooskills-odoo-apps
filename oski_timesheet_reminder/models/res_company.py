from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_timesheet_reminder_active = fields.Boolean(
        string="Rappel de saisie des temps", default=False)
    oski_timesheet_expected_hours = fields.Float(
        string="Heures attendues par semaine", default=35.0,
        help="Utilisé pour les employés dont l'horaire de travail ne dit rien. "
             "Sinon, c'est l'horaire de l'employé qui fait foi.")
    oski_timesheet_tolerance = fields.Float(
        string="Tolérance (heures)", default=1.0,
        help="En deçà de cet écart, l'employé n'est pas dérangé.")
