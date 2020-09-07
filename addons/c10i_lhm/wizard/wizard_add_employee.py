# -*- coding: utf-8 -*-
##############################################################################
#
#    deby@C10i, Consult10Indonesia
#    Copyright (C) 2018 Consult10Indonesia
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################

import time
import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class WizardAddEmployee(models.TransientModel):
    _name           = "wizard.add.employee"
    _description    = "Wizard Add Employee"

    @api.model
    def default_get(self, fields):
        record_ids  = self._context.get('active_ids')
        result      = super(WizardAddEmployee, self).default_get(fields)
        if record_ids:
            lhm_transaction_data = self.env['lhm.transaction'].browse(record_ids)
            if lhm_transaction_data:
                if 'next_number' in fields:
                    result['next_number'] = len(lhm_transaction_data.lhm_line_ids) + 1
                if 'date' in fields:
                    result['date'] = lhm_transaction_data.date
                if 'name' in fields:
                    result['name'] = lhm_transaction_data.name
        return result

    name                = fields.Char("Nama LHM")
    company_id          = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    employee_id         = fields.Many2one(comodel_name="hr.employee", string="Nama Karyawan")
    attendance_id       = fields.Many2one(comodel_name="hr.attendance.type", string="Absensi")
    attendance_type     = fields.Selection([('in', 'Masuk'), ('out', 'Keluar'), ('na', 'N/A'), ('kj', 'KJ')], string='Absensi Type', readonly=True, related="attendance_id.type")
    kemandoran_from_id  = fields.Many2one(comodel_name="hr.foreman", string="Asal Kemandoran")
    kemandoran_to_id    = fields.Many2one(comodel_name="hr.foreman", string="Tujuan Kemandoran")
    next_number         = fields.Integer(string="Nomor Urut")
    date                = fields.Date(string='Tanggal')
    residual_hk         = fields.Float("Sisa HK")

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id and not self.attendance_id:
            return {
                'value'     : {'employee_id': False},
                'warning'   : {'title': _('Kesalahan Input Data'), 'message': _("Isi Absensi Terlebih Dahulu")},
            }
        elif self.employee_id and self.attendance_id:
            if self.attendance_id.type == 'kj':
                list_line       = self.env['lhm.transaction.line'].search([('employee_id','=',self.employee_id.id),('date','=',self.date)])
                if list_line:
                    residual_hk     = 1
                    for line in list_line:
                        if line.lhm_id and line.lhm_id.state not in ['close']:
                            residual_hk = residual_hk - line.work_day
                    return {
                        'value' : {'residual_hk': residual_hk},
                    }
                else:
                    return {
                        'value': {'residual_hk' : 1},
                    }

    @api.onchange('attendance_id')
    def onchange_attendance_id(self):
        record_ids              = self._context.get('active_ids')
        lhm_transaction_data    = self.env['lhm.transaction'].browse(record_ids)
        if self.attendance_id:
            res                     = {}
            self.kemandoran_from_id = False
            self.kemandoran_to_id   = False
            if self.attendance_type in ['na']:
                # list_employee       = []
                # self.employee_id    = False
                # for lhm_line in lhm_transaction_data.lhm_line_ids:
                #     if lhm_line.attendance_id.type not in ['in', 'out']:
                #         list_employee.append(lhm_line.employee_id and lhm_line.employee_id.id)
                # res['domain']   = {
                #     'employee_id'       : [('id','in',list_employee)],
                #     'kemandoran_to_id'  : [('id','!=',lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or [])]
                # }
                # return res
                list_employee       = [x.id for x in self.env['hr.employee'].search([('is_lhm', '=', True)])]
                self.employee_id    = False
                res['domain'] = {
                    'employee_id': [('id', 'in', list_employee),('is_lhm','=',True)],
                }
                return res
            elif self.attendance_type in ['kj']:
                list_employee       = [x.id for x in self.env['hr.employee'].search([('is_lhm','=',True)])]
                self.employee_id    = False
                res['domain']   = {
                    'employee_id'       : [('id','in',list_employee),('is_lhm','=',True)],
                }
                return res
            elif self.attendance_type in ['in']:
                self.employee_id        = False
                self.kemandoran_to_id   = lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or False
                res['domain'] = {
                    'employee_id'       : [('id', 'in', []),('is_lhm','=',True)],
                    'kemandoran_from_id': [('id', '!=', lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or [])]
                }
                return res
            elif self.attendance_type in ['out']:
                self.employee_id        = False
                self.kemandoran_from_id = lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or False
                res['domain'] = {
                    'employee_id'       : [('id', 'in', []),('is_lhm','=',True)],
                    'kemandoran_to_id'  : [('id', '!=', lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or [])]
                }
                return res
            else:
                self.employee_id = False
                return res
        else:
            self.kemandoran_from_id = False
            self.kemandoran_to_id   = False
            self.employee_id        = False


    @api.onchange('kemandoran_from_id', 'kemandoran_to_id')
    def onchange_kemandoran_from_id(self):
        res                     = {}
        record_ids              = self._context.get('active_ids')
        lhm_transaction_data    = self.env['lhm.transaction'].browse(record_ids)
        if self.kemandoran_from_id and self.attendance_type == 'in':
            list_employee       = []
            self.employee_id    = False
            dest_lhm_data       = self.env['lhm.transaction'].search([('kemandoran_id','=',self.kemandoran_from_id.id), ('date','=',self.date)])
            if self.kemandoran_from_id and dest_lhm_data:
                for lhm_line in dest_lhm_data.lhm_line_ids:
                    if lhm_line.attendance_id.type not in ['na', 'in', 'out']:
                        list_employee.append(lhm_line and lhm_line.employee_id and lhm_line.employee_id.id or False)
            if self.kemandoran_from_id and not dest_lhm_data:
                list_employee = self.kemandoran_from_id.employee_ids.ids
            res['domain'] = {
                'employee_id'       : [('id', 'in', list_employee),('is_lhm','=',True)],
                'kemandoran_from_id': [('id', '!=', lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or [])]
            }
            return res
        elif self.kemandoran_to_id and self.attendance_type == 'out':
            list_employee       = []
            self.employee_id    = False
            if self.kemandoran_to_id:
                for lhm_line in lhm_transaction_data.lhm_line_ids:
                    if lhm_line.attendance_id.type not in ['na', 'in', 'out']:
                        list_employee.append(lhm_line and lhm_line.employee_id and lhm_line.employee_id.id or False)
            res['domain'] = {
                'employee_id'       : [('id', 'in', list_employee),('is_lhm','=',True)],
                'kemandoran_to_id'  : [('id', '!=', lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or [])]
            }
            return res
        else:
            return res

    @api.multi
    def add_employee(self):
        record_ids              = self._context.get('active_ids')
        lhm_transaction_data    = self.env['lhm.transaction'].browse(record_ids)
        employee                = self.employee_id
        min_wage = False
        if employee and employee.basic_salary_type == 'employee':
            min_wage = self.env['hr.minimum.wage'].search([('employee_id', '=', employee.id), ('date_from', '<=', lhm_transaction_data.date), ('date_to', '>=', lhm_transaction_data.date)], limit=1)
        elif employee and employee.basic_salary_type == 'employee_type':
            min_wage = self.env['hr.minimum.wage'].search([('employee_type_id', '=', employee.type_id.id), ('date_from', '<=', lhm_transaction_data.date), ('date_to', '>=', lhm_transaction_data.date)], limit=1)
        if not min_wage:
            raise ValidationError(_("UMR belum dibuat untuk tanggal dan karyawan ini!"))
        if self.attendance_type == 'na' and employee and lhm_transaction_data:
            values = {
                'sequence'              : self.next_number,
                'name'                  : employee.no_induk,
                'date'                  : self.date,
                'attendance_id'         : self.attendance_id and self.attendance_id.id or False,
                'employee_id'           : employee.id,
                'min_wage_id'           : min_wage and min_wage.id or False,
                'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)) or False,
                'lhm_id'                : lhm_transaction_data.id,
                'work_day'              : 0.0,
                'work_result'           : 0.0,
                'premi'                 : 0.0,
                'overtime_hour'         : 0.0,
                'overtime_value'        : 0.0,
                'penalty'               : 0.0,
                'non_work_day'          : 0.0,
                'total_hke'             : 0.0,
                'total_hkne'            : 0.0,
                'min_wage_value_date'   : 0.0,
            }
            self.env['lhm.transaction.line'].create(values)
        elif self.attendance_type == 'in' and employee and lhm_transaction_data:
            other_line  = self.env['lhm.transaction.line'].search([('date', '=', self.date),('employee_id','=',self.employee_id.id)], order='id asc', limit=1)
            other_attn  = self.env['hr.attendance.type'].search([('type', '=', 'out')], limit=1)
            other_lhm   = other_line.lhm_id
            if other_lhm and other_lhm.state not in ['draft','in_progress']:
                raise ValidationError(_("Anda tidak dapat memasukkan karyawan di dokumen : %s.\n "
                                        "Karena status dokumen tersebut %s.\n"
                                        "Anda dapat menghubungi user yang bersangkutan atau menghubungi Asisten/Kepala Kebun.") % (other_lhm.name, str(other_lhm.state).title()))
            else:
                pass
            values_transfer     = {
                'name'              : self.name,
                'date'              : self.date,
                'employee_id'       : employee.id,
                'lhm_id'            : lhm_transaction_data.id,
                'type'              : 'in',
                'kemandoran_from_id': self.kemandoran_from_id.id,
                'kemandoran_to_id'  : lhm_transaction_data.kemandoran_id.id,
            }
            new_transfer    = self.env['hr.employee.foreman.transfer'].create(values_transfer)
            values = {
                'sequence'              : self.next_number,
                'name'                  : employee.no_induk,
                'date'                  : self.date,
                'attendance_id'         : self.attendance_id and self.attendance_id.id or False,
                'transfer_id'           : new_transfer and new_transfer.id or False,
                'employee_id'           : employee.id,
                'min_wage_id'           : min_wage and min_wage.id or False,
                'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)) or False,
                'lhm_id'                : lhm_transaction_data.id,
                'work_day'              : 0.0,
                'work_result'           : 0.0,
                'premi'                 : 0.0,
                'overtime_hour'         : 0.0,
                'overtime_value'        : 0.0,
                'penalty'               : 0.0,
                'non_work_day'          : 0.0,
                'total_hke'             : 0.0,
                'total_hkne'            : 0.0,
                'min_wage_value_date'   : 0.0,
            }
            new_trans_line  = self.env['lhm.transaction.line'].create(values)
            new_transfer.write({'lhm_line_id' : new_trans_line and new_trans_line.id or False})
            values_transfer_out = {
                'name'              : "Temporary Out From" + str(self.name),
                'date'              : self.date,
                'employee_id'       : employee.id,
                'type'              : 'out',
                'kemandoran_from_id': lhm_transaction_data.kemandoran_id.id,
                'kemandoran_to_id'  : self.kemandoran_from_id.id,
            }
            if other_line:
                total_progress        = len([x.id for x in other_lhm.process_line_ids])
                if total_progress   >= 1:
                    other_lhm.run_progress()
                new_transfer_out      = self.env['hr.employee.foreman.transfer'].create(values_transfer_out)
                value_update_other    ={
                    'attendance_id'     : other_attn and other_attn.id or False,
                    'transfer_id'       : new_transfer_out and new_transfer_out.id or False,
                    'satuan_id'         : False,
                    'activity_id'       : False,
                    'location_id'       : False,
                    'location_type_id'  : False,
                    'work_day'          : 0.0,
                    'work_result'       : 0.0,
                    'premi'             : 0.0,
                    'overtime_hour'     : 0.0,
                    'overtime_value'    : 0.0,
                    'penalty'           : 0.0,
                }
                other_line.write(value_update_other)
                new_transfer_out.write({
                    'name'              : other_line.lhm_id.name,
                    'lhm_id'            : other_line.lhm_id and other_line.lhm_id.id or False,
                    'lhm_line_id'       : other_line and other_line.id or False,
                    'other_lhm_id'      : lhm_transaction_data and lhm_transaction_data.id or False,
                    'other_lhm_line_id' : new_trans_line and new_trans_line.id or False,
                })
                new_transfer.write({
                    'other_lhm_id'      : other_line.lhm_id and other_line.lhm_id.id or False,
                    'other_lhm_line_id' : other_line and other_line.id or False,
                })
            else:
                new_transfer_out = self.env['hr.employee.foreman.transfer'].create(values_transfer_out)
                new_transfer_out.write({
                    'other_lhm_line_id' : new_trans_line and new_trans_line.id or False,
                    'other_lhm_id'      : lhm_transaction_data and lhm_transaction_data.id or False,
                })
        elif self.attendance_type == 'out' and employee and lhm_transaction_data:
            other_lhm   = self.env['lhm.transaction'].search([('date', '=', self.date), ('kemandoran_id', '=', self.kemandoran_to_id.id)], order='id asc', limit=1)
            if other_lhm:
                year_lhm    = int(datetime.datetime.strptime(other_lhm.date, '%Y-%m-%d').strftime('%Y'))
                min_wage    = self.env['hr.minimum.wage'].search([('year', '=', year_lhm)])
            attn_spec   = [x.id for x in self.env['hr.attendance.type'].search([('type','in',['in','out','na'])])]
            this_line   = self.env['lhm.transaction.line'].search([('date', '=', self.date), ('employee_id', '=', self.employee_id.id), ('attendance_id','not in',attn_spec)], order='id asc', limit=1)
            attn_in     = self.env['hr.attendance.type'].search([('type', '=', 'in')], limit=1)
            if other_lhm and other_lhm.state not in ['draft','in_progress']:
                raise ValidationError(_("Anda tidak dapat memasukkan karyawan di dokumen : %s.\n "
                                        "Karena status dokumen tersebut %s.\n"
                                        "Anda dapat menghubungi user yang bersangkutan atau menghubungi Asisten/Kepala Kebun.") % (other_lhm.name, str(other_lhm.state).title()))
            else:
                pass
            if this_line:
                values_transfer_out  = {
                    'name'                  : self.name or "",
                    'date'                  : self.date or False,
                    'employee_id'           : employee and employee.id or False,
                    'lhm_id'                : lhm_transaction_data and lhm_transaction_data.id or False,
                    'lhm_line_id'           : this_line and this_line.id or False,
                    'type'                  : 'out',
                    'kemandoran_from_id'    : lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or False,
                    'kemandoran_to_id'      : self.kemandoran_to_id and self.kemandoran_to_id.id or False,
                }
                new_transfer_in     = self.env['hr.employee.foreman.transfer'].create(values_transfer_out)
                value_update_this   = {
                    'attendance_id'     : self.attendance_id and self.attendance_id.id or False,
                    'transfer_id'       : new_transfer_in and new_transfer_in.id or False,
                    'satuan_id'         : False,
                    'activity_id'       : False,
                    'location_id'       : False,
                    'location_type_id'  : False,
                    'work_day'          : 0.0,
                    'work_result'       : 0.0,
                    'premi'             : 0.0,
                    'overtime_hour'     : 0.0,
                    'overtime_value'    : 0.0,
                    'penalty'           : 0.0,
                }
                this_line.write(value_update_this)
                values_transfer_in  = {
                    'name'              : "Temporary In From" + str(self.name or ""),
                    'date'              : self.date or False,
                    'employee_id'       : employee and employee.id or False,
                    'other_lhm_id'      : lhm_transaction_data and lhm_transaction_data.id or False,
                    'other_lhm_line_id' : this_line and this_line.id or False,
                    'type'              : 'in',
                    'kemandoran_from_id': self.kemandoran_to_id and self.kemandoran_to_id.id or False,
                    'kemandoran_to_id'  : lhm_transaction_data and lhm_transaction_data.kemandoran_id and lhm_transaction_data.kemandoran_id.id or False,
                }
                new_transfer_in = self.env['hr.employee.foreman.transfer'].create(values_transfer_in)
            if other_lhm:
                other_seq_no    = len([x.id for x in other_lhm.lhm_line_ids])
                values_other    = {
                    'sequence'              : other_seq_no + 1,
                    'name'                  : employee and employee.no_induk or False,
                    'date'                  : self.date or False,
                    'attendance_id'         : attn_in and attn_in.id or False,
                    'transfer_id'           : new_transfer_in and new_transfer_in.id or False,
                    'employee_id'           : employee and employee.id or False,
                    'min_wage_id'           : min_wage and min_wage.id or False,
                    'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)) or False,
                    'lhm_id'                : other_lhm.id,
                    'work_day'              : 0.0,
                    'work_result'           : 0.0,
                    'premi'                 : 0.0,
                    'overtime_hour'         : 0.0,
                    'overtime_value'        : 0.0,
                    'penalty'               : 0.0,
                    'non_work_day'          : 0.0,
                    'total_hke'             : 0.0,
                    'total_hkne'            : 0.0,
                    'min_wage_value_date'   : 0.0,
                }
                new_trans_line = self.env['lhm.transaction.line'].create(values_other)
                new_transfer_in.write({
                    'lhm_line_id'   : new_trans_line and new_trans_line.id or False,
                    'lhm_id'        : other_lhm and other_lhm.id or False,
                })
        elif self.attendance_type == 'kj' and employee and lhm_transaction_data:
            values = {
                'sequence'              : self.next_number,
                'name'                  : employee.no_induk,
                'date'                  : self.date,
                'attendance_id'         : self.attendance_id and self.attendance_id.id or False,
                'employee_id'           : employee.id,
                'min_wage_id'           : min_wage and min_wage.id or False,
                'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)) or False,
                'lhm_id'                : lhm_transaction_data.id,
                'work_day'              : self.residual_hk,
                'work_result'           : 0.0,
                'premi'                 : 0.0,
                'overtime_hour'         : 0.0,
                'overtime_value'        : 0.0,
                'penalty'               : 0.0,
                'non_work_day'          : 0.0,
                'total_hke'             : 0.0,
                'total_hkne'            : 0.0,
                'min_wage_value_date'   : 0.0,
            }
            self.env['lhm.transaction.line'].create(values)
        else:
            raise UserError(_('We found some error, maybe the data was broken. Please Contact Administrator to fix this error'))