# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountCostCenter(models.Model):
    _inherit = 'account.cost.center'

    default_salary_account_id = fields.Many2one('account.account', 'Default Salary Account')

    @api.model
    def create(self, values):
        result  = super(AccountCostCenter, self).create(values)
        if 'default_salary_account_id' in values and result.location_id:
            result.location_id.write({'default_salary_account_id': values.get('default_salary_account_id', False)})
        return  result

    @api.multi
    def write(self, values):
        if self.default_salary_account_id and self.location_id:
            self.location_id.write({'default_salary_account_id': self.default_salary_account_id and self.default_salary_account_id.id or False})
        if 'default_salary_account_id' in values and self.location_id:
            self.location_id.write({'default_salary_account_id': values.get('default_salary_account_id', False)})
        return super(AccountCostCenter, self).write(values)