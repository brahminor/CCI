{
    'name': 'CCI France',
    'summary': """Module principale du projet CCI France Intl""",
    'version': '0.0.1',
    'description': """
    CCI France Internaional
    =======================
    Application Gestion des membres
    """,
    'author': 'Clovis NZOUENDJOU, Anybox',
    'company': 'Anybox SAS',
    'website': 'http://www.anybox.fr',
    'category': 'Customs',
    'depends': [
        'membership',
        'sale',

    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/membership_invoice_view.xml',
        'views/partner_view.xml',
        'views/membership_view.xml',
        'views/product_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
