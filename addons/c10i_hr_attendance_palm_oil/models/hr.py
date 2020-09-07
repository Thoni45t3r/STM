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


class hr_employee(models.Model):
    _inherit        = 'hr.employee'
    _description    = 'Employee'

    type_id                                         = fields.Many2one(comodel_name="hr.employee.type", string='Tipe Karyawan', ondelete="restrict")
    basic_salary_type                               = fields.Selection(selection=[('employee','Karyawan'), ('employee_type','Tipe Karyawan')], string="Acuan Gaji Pokok", default="employee_type")
    umr_ids                                         = fields.One2many(comodel_name="hr.minimum.wage", inverse_name="employee_id", string="History UMR")
    default_location_type_id                        = fields.Many2one('account.location.type', string="Tipe Lokasi", ondelete="restrict")
    default_location_id                             = fields.Many2one('account.location', string="Lokasi", ondelete="restrict")
    default_account_salary_id                       = fields.Many2one('account.account', string="Gaji", ondelete="restrict")
    ## Group Of Allowance
    default_account_overtime_id                     = fields.Many2one('account.account', 'Lembur', ondelete="restrict")
    default_account_incentive_id                    = fields.Many2one('account.account', 'Insentif', ondelete="restrict")
    default_account_holiday_allowance_id            = fields.Many2one('account.account', 'THR ', ondelete="restrict")
    default_account_food_transport_allowance_id     = fields.Many2one('account.account', 'Transport & Makan', ondelete="restrict")
    default_account_medical_allowance_id            = fields.Many2one('account.account', 'Pengobatan', ondelete="restrict")
    default_account_welfare_allowance_id            = fields.Many2one('account.account', 'Kesejahteraan', ondelete="restrict")
    default_account_bpjs_allowance_id               = fields.Many2one('account.account', 'Asuransi Kesehatan', ondelete="restrict")
    default_account_ketenagakerjaan_allowance_id    = fields.Many2one('account.account', 'Asuransi Ketenagakerjaan', ondelete="restrict")
    default_account_pensiun_allowance_id            = fields.Many2one('account.account', 'Asuransi Pensiun', ondelete="restrict")
    default_account_keselamatan_allowance_id        = fields.Many2one('account.account', 'Asuransi JKK + JKM', ondelete="restrict")
    inter_account_bpjs_allowance_id                 = fields.Many2one('account.account', 'Inter Asuransi Kesehatan', ondelete="restrict")
    inter_account_ketenagakerjaan_allowance_id      = fields.Many2one('account.account', 'Inter Asuransi Ketenagakerjaan', ondelete="restrict")
    inter_account_pensiun_allowance_id              = fields.Many2one('account.account', 'Inter Asuransi Pensiun', ondelete="restrict")
    inter_account_keselamatan_allowance_id          = fields.Many2one('account.account', 'Inter Asuransi JKK + JKM', ondelete="restrict")
    #
    food_transport                                  = fields.Boolean("Transport & Makan", help="Have Transport & Makan")
    medical                                         = fields.Boolean("Pengobatan", help="Have Pengobatan")
    welfare                                         = fields.Boolean("Kesejahteraan", help="Have Kesejahteraan")
    incentive                                       = fields.Boolean("Insentif", help="Have Insentif")
    is_npwp                                         = fields.Boolean("Is NPWP?", help="Have NPWP")
    ## Insurance
    kesehatan                                       = fields.Boolean("Kesehatan", help="Have BPJS Kesehatan")
    kesehatan_date_start                            = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan BPJS Kesehatan")
    ketenagakerjaan                                 = fields.Boolean("Ketenagakerjaan", help="Have BPJS Ketenagakerjaan")
    ketenagakerjaan_date_start                      = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan BPJS Ketenagakerjaan")
    bpjs_pensiun                                    = fields.Char('BPJS Pensiun', )
    pensiun                                         = fields.Boolean("Pensiun", help="Have BPJS Pensiun")
    pensiun_date_start                              = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan BPJS Pensiun")
    bpjs_keselamatan                                = fields.Char('BPJS JKK + JKM', )
    keselamatan                                     = fields.Boolean("Keselamatan", help="Have Asuransi JKK + JKM")
    keselamatan_date_start                          = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan Asuransi JKK + JKM")


    @api.onchange('default_location_type_id')
    def _onchange_default_location_type_id(self):
        if self.default_location_type_id:
            self.default_location_id        = False
            self.default_account_salary_id  = False

    @api.onchange('default_location_id')
    def _onchange_default_location_id(self):
        if self.default_location_id:
            self.default_account_salary_id    = self.default_location_id and self.default_location_id.default_salary_account_id and self.default_location_id.default_salary_account_id.id or False

class hr_minimum_wage(models.Model):
    _inherit        = 'hr.minimum.wage'
    _description    = 'Minimum Wage Management'

    @api.model
    def _get_state(self):
        for state in self:
            all_umr = self.env['hr.minimum.wage'].search([('id', '!=', state.id),
                                                          ('year', '=', state.year),
                                                          ('date_to', '>', state.date_to),
                                                          ('employee_id', '=', self.employee_id and self.employee_id.id or False),
                                                          ('employee_type_id', '=', self.employee_type_id and self.employee_type_id.id or False),
                                                          ('basic_salary_type', '=', self.basic_salary_type),
                                                          ])
            if all_umr:
                state.state = 'notactive'
            else:
                state.state = 'active'

    basic_salary_type   = fields.Selection(selection=[('employee', 'Karyawan'), ('employee_type', 'Tipe Karyawan')], string="Acuan Gaji Pokok")
    umr_day             = fields.Float(string="UMR(Hari)", compute='_compute_worked_hours', store=True, readonly=True)
    work_day            = fields.Integer(string="Hari Kerja", default=25)
    employee_id         = fields.Many2one(comodel_name="hr.employee", string="Karyawan", ondelete="restrict")
    employee_type_id    = fields.Many2one(comodel_name="hr.employee.type", string="Type Karyawan", ondelete="restrict")

    @api.depends('umr_month', 'work_day')
    def _compute_worked_hours(self):
        for umr in self:
            if (umr.umr_month > 0) and (umr.work_day > 0):
                umr.umr_day = umr.umr_month / umr.work_day

    #@overriding
    @api.onchange('year', 'date_from', 'date_to', 'employee_id', 'employee_type_id', 'basic_salary_type')
    def onchange_date_and_year(self):
        domain  = [('id', '!=', self._origin.id), ('year', '=', self.year), ('basic_salary_type', '=', False)]
        if self.employee_id:
            domain = [('id', '!=', self._origin.id), ('year', '=', self.year), ('employee_id', '=', self.employee_id and self.employee_id.id or False)]
        elif self.employee_type_id:
            domain = [('id', '!=', self._origin.id), ('year', '=', self.year), ('employee_type_id', '=', self.employee_type_id and self.employee_type_id.id or False)]
        other_ids = self.env['hr.minimum.wage'].search(domain, order="date_to asc")
        if other_ids:
            other_ids = other_ids[-1]  # <--- mengambil tanggal akhir paling besar
        else:
            other_ids = False
        if self.basic_salary_type and self.basic_salary_type == 'employee':
            self.employee_type_id   = False
        elif self.basic_salary_type and self.basic_salary_type == 'employee_type':
            self.employee_id        = False
        if self.date_to and (self.employee_id or self.employee_type_id):
            if self.date_to and self.date_to <= self.date_from:
                res = {}
                self.date_to = fields.Date.from_string(self.date_from) + relativedelta(days=1)
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Tanggal Berakhir Harus Lebih Besar dari Tanggal Mulai")},
                }
            elif self.year and int(fields.Date.from_string(self.date_to).strftime('%Y')) != self.year:
                res             = {}
                res['warning']  = {'title': _('Kesalahan Input Data'),
                                    'message': _("Tanggal %s tidak dalam tahun: %s.") % (self.date_to, self.year)}
                self.date_to    = time.strftime(str(self.year) + '-12-31')
                return res
        if self.year:
            if self.year and other_ids and other_ids.date_to == time.strftime(str(self.year) + '-12-31') and (self.employee_id or self.employee_type_id):
                res             = {}
                res['warning']  = {'title': _('Kesalahan Input Data'),
                                    'message': _("Semua range tanggal pada tahun %s sudah didefinisikan") % self.year}
                self.year       = False
                return res
            elif self.year and other_ids:
                res = {}
                self.date_from  = fields.Date.from_string(other_ids.date_to) + relativedelta(days=1)
                # self.date_to    = time.strftime(str(self.year) + '-12-31')
                return res
            elif self.year and not other_ids:
                res = {}
                self.date_from  = time.strftime(str(self.year) + '-01-01')
                self.date_to    = time.strftime(str(self.year) + '-12-31')

class hr_employee_type(models.Model):
    _name           = 'hr.employee.type'
    _description    = 'Employee Type'

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    sequence_id         = fields.Many2one(comodel_name="ir.sequence", string="Sequence", ondelete="restrict")
    overtime_calc       = fields.Boolean("Calculate Overtime", default=False)
    monthly_employee    = fields.Boolean("Monthly Employee", default=False)
    bhl_employee        = fields.Boolean("BHL Employee", default=False)
    contract_employee   = fields.Boolean("Contract Employee", default=False)
    other_employee      = fields.Boolean("Other Employee", default=False)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active              = fields.Boolean("Active", default=True)
    umr_ids             = fields.One2many(comodel_name="hr.minimum.wage", inverse_name="employee_type_id", string="History UMR")