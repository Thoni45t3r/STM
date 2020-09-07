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
    _description    = 'Account Cost Center Plantation Inherit'

    def _default_location_type(self):
        location_type_ids   = self.env['lhm.location.type'].search([('general_charge','=',True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    plantation          = fields.Boolean("Plantation", default=False)
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    active              = fields.Boolean("Active", default=True)
    owner_type          = fields.Selection([('inti','Inti'),('plasma','Plasma')], 'Tipe Kepemilikan Blok')

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values     = {
            'name'              : location_name or "(NoName)",
            'code'              : location_code or "(NoCode)",
            'type_id'           : location_type_id or False,
            'group_progress_id' : group_progress_id,
        }
        new_location = False
        location = super(AccountCostCenter, self).create(values)
        if location.plantation:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(AccountCostCenter, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(AccountCostCenter, self).unlink()
        return location

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
        lhm_location_type = self.search(domain + args, limit=limit)
        return lhm_location_type._name_get()