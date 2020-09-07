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
    'name'      : "Human Resource Attendances Indonesia",
    'category'  : 'Human Resources',
    'version'   : '1.0.0.1',
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'c10i_base', 'hr', 'c10i_hr', 'hr_attendance'],
    'summary'   : """
                        HR Attendances Module Indonesia - C10i
                        Managemen Kehadiran Karyawan
                    """,
    'description'   : """
Digunakan untuk managemen kehadiran karyawan.
=============================================

Features:
---------
- Manual Import Biometric/Fingerprint
- Overtime Configuration

                    """,
    'data'      : [
        "security/ir.model.access.csv",
        "data/sequence_number_data.xml",
        "views/hr_employee_view.xml",
        "views/hr_attendance_view.xml",
        "views/hr_attendance_import_view.xml",
        "views/res_config_view.xml"
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
