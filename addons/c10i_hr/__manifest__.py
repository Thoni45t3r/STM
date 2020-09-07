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
    'name'      : "Human Resource Indonesia",
    'category'  : 'Human Resources',
    'version'   : '1.0.0.1',
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'c10i_base', 'hr', 'hr_contract', 'hr_public_holidays'],
    'summary'   : """
                        HR Module Indoseia - C10i
                    """,
    'description'   : """
                        Modul Human Resource yang sudah dikustom untuk keperluan Managemen HR di Indonesia.
                    """,
    'data'      : [
                    'data/base_data.xml',
                    'data/hide_menu_data.xml',
                    'views/hr_views.xml',
                    'views/hr_contract_views.xml',
                    'views/hr_public_holidays_view.xml',
                    'views/res_company_views.xml',
                    'data/ptkp_default_data.xml',
                    'data/religion_default_data.xml',
                    'data/sequence_number_data.xml',
                    'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
