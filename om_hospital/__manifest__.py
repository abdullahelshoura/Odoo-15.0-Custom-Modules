# -*- coding: utf-8 -*-
{
    'name': "Hospital Managment",
    'sequence': -100,
    'summary': """Patients Treatment Programs""",
    'application': True,
    'description': """""",

    'author': "abdullah elshoura",
    'website': "hospital.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Health Care',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['mail', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/patient_tag_data.xml',
        'data/patient.tag.csv',
        'data/sequence_data.xml',
        'views/menu.xml',
        'views/patient_view.xml',
        'views/female_patient_view.xml',
        'wizard/cancel_appointment_wizard.xml',
        'views/appointment_view.xml',
        'views/patient_tag_view.xml',
        'views/odoo_playground_view.xml',
        'views/res_config_settings_views.xml',
        'views/operation_view.xml',
        'report/patient_card.xml',
        'report/report.xml',

    ],
    # # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
