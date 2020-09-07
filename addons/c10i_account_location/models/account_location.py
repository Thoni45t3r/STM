# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo.addons import decimal_precision as dp
import time

class AccountLocationType(models.Model):
    _name           = 'account.location.type'
    _description    = 'Account Location Type'
    _order          = 'code, name'

    name = fields.Char("Name", required=True)
    code = fields.Char("Code", required=True)
    account_id = fields.Many2one("account.account", string="Allocation", ondelete="restrict")
    location_ids = fields.One2many("account.location", "type_id", string="Daftar Lokasi")
    account_ids     = fields.Many2many('account.account', 'rel_location_type_account', 'location_type_id', 'account_id', string='Daftar Account')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active = fields.Boolean("Active", default=True)
    no_location = fields.Boolean("Empty Location", help="This will not show you location mapped inside")
    general_charge = fields.Boolean("General Charge", help="Filtering for General Charge")

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
        AccountLocationType = self.search(domain + args, limit=limit)
        return AccountLocationType._name_get()

class AccountLocation(models.Model):
    _name           = 'account.location'
    _description    = 'Account Location'

    name                = fields.Char("Name", required=True)
    code                = fields.Char("Code", required=True)
    type_id             = fields.Many2one("account.location.type", string="Tipe", ondelete="restrict")
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active              = fields.Boolean("Active", default=True)
    
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
        AccountLocation = self.search(domain + args, limit=limit)
        return AccountLocation._name_get()
