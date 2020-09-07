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

from odoo import models, fields, tools, api, exceptions, _
from odoo.osv import expression

class hr_employee(models.Model):
    _inherit        = 'hr.employee'
    _description    = 'Employee Management'

    biometric = fields.Char(string="Biometric ID", help="ID used for employee identification from fingerprint.", copy=False)

    @api.constrains('biometric')
    def _check_biometic_validity(self):
        for employee in self:
            if employee.biometric:
                biometric_before = self.env['hr.employee'].search([('biometric', '=', employee.biometric), ('id', '!=', employee.id),], limit=1)
                if biometric_before:
                     raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s.\nThe Biometric ID was already taken by %(empl_name_before)s") % {
                            'empl_name'         : employee.name_related,
                            'empl_name_before'  : biometric_before.name_related,
                        })