# -*- coding: utf-8 -*-
{
    'name': "Personal Module",
    'sequence': 0,
    'application': True,
    'summary': """Personal Information""",
    'description': """""",
    'author': "AECompany",
    'website': "",
    'category': 'Personal File',
    'version': '0.1',
    'depends': ['base', 'mail', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cancel_journal_view.xml',
        'data/sequence_data.xml',
        'views/menu_items.xml',
        'views/personal_info_view.xml',
        'views/personal_tag_view.xml',
        'views/person_depends.xml',
    ],
}
