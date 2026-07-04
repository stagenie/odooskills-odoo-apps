{
    'name': 'Treasury — Cash & Safe Management',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Cash registers, safes, closings, transfers, configurable GL entries',
    'description': 'Complete physical treasury management: cash registers with running '
                   'balance and chained closings, safes, 9-way transfers, operation '
                   'categories, configurable accounting entries, payment integration.\n\n'
                   'Design notes\n'
                   '------------\n'
                   '(a) A payment posted by a user who has NO treasury access group '
                   'creates no mirror treasury operation: the register balance and the '
                   'journal balance stay in sync only for payments recorded by treasury '
                   'users. Grant the relevant treasury group to a user before their '
                   'payments should feed the cash register / bank / safe balances.\n'
                   '(b) Cancelling or resetting a payment to draft always enforces the '
                   'closing locks for every user (a locked/closed period blocks it '
                   'regardless of who triggers it), and the resulting mirror-operation '
                   'cleanup runs under a payment-scoped sudo: the treasury record rules '
                   '(per-assignment access to registers/safes/banks) are not meant to '
                   'restrict a payment from maintaining its own mirror operation.',
    'author': 'OdooSkills',
    'website': 'https://odooskills.com',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'security/treasury_groups.xml',
        'security/ir.model.access.csv',
        'data/treasury_sequence_data.xml',
        'data/treasury_category_data.xml',
        'data/treasury_cron_data.xml',
        'views/menu_views.xml',
        'views/treasury_operation_category_views.xml',
        'views/treasury_cash_views.xml',
        'views/treasury_cash_operation_views.xml',
        'views/treasury_cash_closing_views.xml',
        'views/treasury_safe_views.xml',
        'views/treasury_transfer_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_views.xml',
        'security/treasury_rules.xml',
        'reports/treasury_cash_closing_report.xml',
        'reports/treasury_transfer_report.xml',
    ],
    'installable': True,
    'application': True,
}
