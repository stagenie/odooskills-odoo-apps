from odoo.tests import TransactionCase


class SchoolCase(TransactionCase):
    """Structure minimale : une période ouverte, un programme collège 2 niveaux."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.period = cls.env['oski.school.period'].create({
            'name': '2026-2027', 'code': '26-27', 'period_type': 'year',
            'date_start': '2026-09-01', 'date_end': '2027-06-30',
        })
