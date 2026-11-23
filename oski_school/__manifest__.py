{
    'name': 'School Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Education',
    'summary': "Run a private school: periods, programs, classes, students and "
               "guardians, enrollments with seat control, year-end promotion.",
    'description': """
Open-source core of the School suite — for primary, middle school, high school,
higher education, a language center or a vocational training center.

- Periods (school year, semester, session) with generated terms.
- Programs typed by cycle, levels, subjects, rooms, classes.
- Students with guardians, automatic student ID, teachers.
- Enrollments with seat control, required guardian and withdrawal.
- Year-end promotion wizard (promoted / repeating / left) and structure duplication.
- Enrollment certificate and class list (PDF).

The paid modules of the suite add admissions and online enrollment,
tuition fees and online payment, timetable, attendance, grades and
report cards, teacher workspace, dashboard and communication.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
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
        'reports/report_actions.xml',
        'reports/report_enrollment_certificate.xml',
        'reports/report_class_list.xml',
    ],
    'demo': ['demo/school_demo.xml'],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_students.png",
        "static/description/screenshot_02_student_form.png",
        "static/description/screenshot_03_classes.png",
        "static/description/screenshot_04_class_form.png",
        "static/description/screenshot_05_promotion.png",
        "static/description/screenshot_06_certificate.png",
    ],
    'installable': True,
    'application': True,
}
