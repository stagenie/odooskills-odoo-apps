{
    'name': 'OdooSkills — School: students, classes, enrollments',
    'version': '19.0.1.0.0',
    'category': 'Services/Education',
    'summary': 'The free core of the School suite: academic structure, students '
               'and guardians, teachers, enrollments and year-end promotion.',
    'description': """
Run any private school — primary, middle, high, higher education, language
centre or vocational training — on one generic core.

- Periods (school year, semester, rolling session) with grading terms.
- Programs typed by cycle, levels, subjects, rooms, classes.
- Students with guardians, registration numbers, teachers.
- Enrollments with seat control, guardian requirement and withdrawal.
- Year-end promotion wizard (promoted / repeated / left) and structure duplication.
- Enrollment certificate and class list (PDF).

Paid satellites add admission, online application, fees and online payment,
timetable, attendance, grades and report cards, teacher workspace, dashboard
and communication.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': ['mail', 'contacts'],
    'data': [
        'security/school_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/period_views.xml',
        'views/program_views.xml',
        'views/teacher_views.xml',
        'views/student_views.xml',
        'views/school_class_views.xml',
        'views/enrollment_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
}
