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
import calendar
from dateutil.relativedelta import relativedelta

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class AccountCostCenter(models.Model):
    _inherit        = 'account.cost.center'
    _description    = 'Account Cost Center'

    def _default_location_type(self):
        location_type_ids   = self.env['account.location.type'].search([('general_charge','=',True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    location_id = fields.Many2one("account.location", string="Lokasi")
    location_type_id = fields.Many2one("account.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    active = fields.Boolean("Active", default=True)
    type                = fields.Selection([('cc', 'Cost Center'), ('foh', 'Factory Overhead')], string='Type')
    
    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        location_values     = {
            'name'              : location_name or "(NoName)",
            'code'              : location_code or "(NoCode)",
            'type_id'           : location_type_id or False,
        }
        new_location = False
        cost_center = super(AccountCostCenter, self).create(values)
        
        new_location = self.env['account.location'].create(location_values)
        if new_location:
            cost_center.location_id = new_location.id
        return cost_center

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(AccountCostCenter, self).write(values)

    @api.multi
    def unlink(self):
        for cost_center in self:
            if cost_center.location_id:
                cost_center.location_id.unlink()
        cost_center = super(AccountCostCenter, self).unlink()
        return cost_center

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, record.code))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result

    @api.multi
    def _name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, record.code + " - " + record.name))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        cost_center = self.search(domain + args, limit=limit)
        return cost_center._name_get()