# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import time
import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import base64
import xlrd
from xlrd import open_workbook, XLRDError
from odoo import models, fields, tools, exceptions, api, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
class hr_attendance(models.Model):
    _inherit        = 'hr.attendance'

    employee_salary         = fields.Float("Gaji")
    overtime_hours_total    = fields.Float("Total Lembur")
    overtime_hours_value    = fields.Float("Lembur/ Jam")
    note                    = fields.Text("Keterangan")
    hk                      = fields.Float("Hari Kerja")
    holiday                 = fields.Boolean("Hari Libur")



