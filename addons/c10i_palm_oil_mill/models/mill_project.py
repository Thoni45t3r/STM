# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import logging
import time
import datetime
import calendar
from odoo.tools.translate import _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import base64
import xlrd

###################################################### Master Project #######################################################
class mill_project_type(models.Model):
    _name           = 'mill.project.type'
    _description    = 'Mill Project Category'

    name        = fields.Char('Name', required=True)
    account_id  = fields.Many2one('account.account', 'Expense Account', required=True)

class mill_project(models.Model):
    _name           = 'mill.project'
    _description    = 'Mill Project'

    def _default_location_type(self):
        location_type_ids = self.env['account.location.type'].search([('project', '=', True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    def _default_dest_location_type(self):
        location_type_ids = self.env['account.location.type'].search([('project', '=', False)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    @api.model
    def _get_user_currency(self):
        currency_id = self.env['res.users'].browse(self._uid).company_id.currency_id
        return currency_id or self.company_id.currency_id

    @api.one
    @api.depends('line_ids.value', 'line_ids.vat')
    def _compute_project_value(self):
        total_vat   = 0
        total_value = 0
        for line in self.line_ids:
            if line.vat >= 1 and line.value >=1:
                total_vat += (line.vat * line.value)/100
            if line.value:
                total_value += line.value
        self.project_value  = total_value
        self.project_ppn    = total_vat
        self.project_nett   = total_vat + total_value

    name                    = fields.Char("Deskripsi")
    code                    = fields.Char("Nomor Project")
    location_id             = fields.Many2one(comodel_name="account.location", string="Lokasi")
    location_type_id        = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi Project", ondelete="restrict", default=_default_location_type)
    dest_location_type_id   = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi Tujuan", ondelete="restrict", default=_default_dest_location_type)
    location_code           = fields.Char("Kode Lokasi", related="location_id.code")
    executor                = fields.Selection([('swakelola', 'Swakelola'), ('contractor', 'Kontraktor')], string='Pelaksana')
    pk_number               = fields.Char("Nomor PK")
    date_start              = fields.Date("Tanggal Mulai")
    date_finished           = fields.Date("Tanggal Selesai")
    qty                     = fields.Float("Qty")
    satuan_id               = fields.Many2one(comodel_name="product.uom", string="Satuan", ondelete="restrict")
    project_value           = fields.Float("Nilai", compute="_compute_project_value", store=False)
    project_ppn             = fields.Float("PPN", compute="_compute_project_value", store=False)
    project_nett            = fields.Float("Nilai Nett", compute="_compute_project_value", store=False)
    date_issue              = fields.Date("Tanggal Terbit")
    active                  = fields.Boolean("Active", default=True)
    note                    = fields.Text("Catatan")
    line_ids                = fields.One2many('mill.project.line', 'project_id', string="Detail Project", )
    currency_id             = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._get_user_currency())
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state                   = fields.Selection(selection=[('draft','New'),('cancel','Cancelled'),('in_progress','Progress'),('done','Done')],
                                                string='Status', copy=False, default='draft', index=False, readonly=False,
                                                help="* New: Project baru.\n"
                                                    "* Cancelled: Project Dibatalkan.\n"
                                                    "* Progress: Project sedang dalam Proses.\n"
                                                    "* Done: Project Sudah Selesai. \n")
    categ_id                = fields.Many2one('mill.project.type', 'Kategory')

    @api.multi
    def button_progress(self):
        if not self.location_id:
            location_name       = self.code
            location_code       = self.name
            location_type_id    = self.location_type_id
            location_values     = {
                'name'      : location_name or "(NoName)",
                'code'      : location_code or "(NoCode)",
                'type_id'   : location_type_id and location_type_id.id or False,
            }
            new_location = self.env['account.location'].create(location_values)
            if new_location:
                 self.location_id = new_location.id
        else:
            self.location_id.write({'active': True})
        self.state = 'in_progress'

    @api.multi
    def button_cancel(self):
        if self.location_id:
            self.location_id.write({'active': False})
        self.state = 'cancel'

    @api.multi
    def button_draft(self):
        if self.location_id:
            self.location_id.write({'active': False})
        self.state = 'draft'

    @api.multi
    def button_done(self):
        if self.location_id:
            self.location_id.write({'active': True})
        self.state = 'done'

    @api.onchange('location_type_id')
    def onchange_attendance_id(self):
        res = {}
        if self.location_type_id:
            self.subtype_project_id = False
        return res

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        location_values     = {
            'name'      : location_name or "(NoName)",
            'code'      : location_code or "(NoCode)",
            'type_id'   : location_type_id or False,
        }
        new_location = False
        location = super(mill_project, self).create(values)
        if location:
            new_location = self.env['account.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'code': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'name': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(mill_project, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(mill_project, self).unlink()
        return location

class mill_project_line(models.Model):
    _name           = 'mill.project.line'
    _description    = 'Mill Project Line'

    name            = fields.Char("Deskripsi", related="location_id.name")
    location_id     = fields.Many2one(comodel_name="account.location", string="Lokasi", ondelete="restrict")
    vat             = fields.Float("PPN(%)")
    value           = fields.Float("Nilai")
    project_id      = fields.Many2one(comodel_name="mill.project", string="Project", ondelete="cascade")
################################################### End Of Master Project ###################################################