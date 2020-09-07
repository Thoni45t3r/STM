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
import urllib3
from lxml import etree
import time

class AccountMove(models.Model):
    _inherit = "account.move"
    
    @api.multi
    def post(self):
        ml_obj = self.env['account.move.line']
        default_loc_type = self.env['account.location.type'].search([('name','=','-')])
        for move in self:
            for line in move.line_ids:
                if not line.account_location_type_id:
                    line.account_location_type_id = default_loc_type and default_loc_type[0].id or False
        return super(AccountMove, self).post()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_location_type_id = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi", ondelete="restrict")
    account_location_id      = fields.Many2one(comodel_name="account.location", string="Lokasi", ondelete="restrict")
    account_location_type_no_location = fields.Boolean(string="Plantation Validator", related="account_location_type_id.no_location")

    @api.onchange('account_location_type_id')
    def _onchange_account_location_type_id(self):
        if self.account_location_type_id:
            self.account_location_id = False
            if self.account_location_type_id.no_location and (self.account_location_type_id.general_charge):
                self.account_id = False
            else:
                self.account_id = self.account_location_type_id.account_id and self.account_location_type_id.account_id.id or False