{
    'name': 'École — élèves, classes, inscriptions',
    'version': '19.0.1.0.0',
    'category': 'Services/Education',
    'summary': "Gérez une école privée : périodes, programmes, classes, élèves et "
               "tuteurs, inscriptions avec contrôle des places, passage d'année",
    'description': """
Cœur gratuit de la suite École — pour le primaire, le collège, le lycée, le
supérieur, un centre de langues ou de formation professionnelle.

- Périodes (année scolaire, semestre, session) avec trimestres générés.
- Programmes typés par cycle, niveaux, matières, salles, classes.
- Élèves avec tuteurs, matricule automatique, enseignants.
- Inscriptions avec contrôle des places, tuteur obligatoire et retrait.
- Assistant de passage d'année (admis / redoublant / parti) et duplication de structure.
- Certificat de scolarité et liste de classe (PDF).

Les modules payants de la suite ajoutent admissions et inscription en ligne,
frais de scolarité et paiement en ligne, emploi du temps, présences, notes et
bulletins, espace enseignant, tableau de bord et communication.
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
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
