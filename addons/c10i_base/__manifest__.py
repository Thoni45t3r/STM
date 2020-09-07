# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

{
    'name'      : 'Base Module of Consult10 Indonesia',
    'version'   : '1.0.1.1',
    'category'  : 'C10i Module',
    'description': """
    -
    """,
    'summary'   : """
                    Base Module modified by Consult10 Indonesia to localization use in Indonesia
                    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'backend_theme_v10', 'jasper_reports', 'web_readonly_bypass', 'web_widget_image_webcam', 'web_widget_float_formula',
                    'web_no_bubble', 'table_header_freeze', 'rowno_in_tree', 'database_cleanup',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/base_data.xml',
        'data/res.state.city.csv',
        'data/res_groups_data.xml',
        'data/ir_config_parameter_background.xml',
        'templates/website_templates.xml',
        'templates/webclient_templates.xml',
        'views/base_views.xml',
        'views/res_company_views.xml',
        'views/res_bank_views.xml',
        'views/res_partner_views.xml',
        'views/res_state_city_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
