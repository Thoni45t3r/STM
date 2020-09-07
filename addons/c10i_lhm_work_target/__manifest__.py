# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

{
    'name'      : "Plantation - LHM Work Target",
    'category'  : 'Plantation',
    'version'   : '0.1',
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['c10i_base', 'c10i_hr', 'c10i_lhm'],
    'summary'   : """
                        Modul Laporan Harian Mandor (LHM) - Odoo 10
                    """,
    'description'   : """
                        Modul Laporan Harian Mandor (LHM) yaitu laporan progress fisik dan biaya untuk penggajian karyawan di lapangan.
                    """,
    'data'      : [
                    'security/ir.model.access.csv',
                    'data/ir_cron_data.xml',
                    'views/lhm_views.xml',
                    'views/hr_views.xml',
                    'wizard/wizard_target_salary_bill_views.xml',
                    'wizard/wizard_du_target_confirmation_views.xml',
                    'views/plantation_salary_views.xml',
                    'report/report_views.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
