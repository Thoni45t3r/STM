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

    import_id       = fields.Many2one(comodel_name="hr.attendance.import", string="Import")
    check_in        = fields.Datetime(string="Check In")
    check_out       = fields.Datetime(string="Check Out")
    rest_in         = fields.Datetime(string="Rest In")
    rest_out        = fields.Datetime(string="Rest Out")
    total_time      = fields.Float("Total Time")
    working_time    = fields.Float("Work Time")
    rest_time       = fields.Float("Rest Time")
    overtime        = fields.Float("Overtime")
    work_day_time   = fields.Float("Work Days Time")

    @api.onchange('check_in', 'check_out')
    def onchange_total_time(self):
        if self.check_in or self.check_out:
            if self.check_in and self.check_out:
                self.total_time         = self.calculate_time_between_date(self.check_out, self.check_in)
                self.working_time       = (self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)
                self.work_day_time      = self.working_day_time(self.check_in, self.env.user.company_id)
                if ((self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)) - self.working_day_time(self.check_in, self.env.user.company_id) > 0:
                    self.overtime = ((self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)) - self.working_day_time(self.check_in, self.env.user.company_id)

    @api.onchange('rest_in', 'rest_out')
    def onchange_rest_time(self):
        if self.rest_out or self.rest_in:
            if self.rest_in and self.rest_out:
                self.rest_time          = self.calculate_time_between_date(self.rest_in, self.rest_out)
                self.working_time       = (self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)
                self.work_day_time      = self.working_day_time(self.check_in, self.env.user.company_id)
                if ((self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)) - self.working_day_time(self.check_in, self.env.user.company_id) > 0:
                    self.overtime = ((self.calculate_time_between_date(self.check_out, self.check_in) or 0.0) - (self.calculate_time_between_date(self.rest_in, self.rest_out) or 0.0)) - self.working_day_time(self.check_in, self.env.user.company_id)

    def working_day_time(self, date, company_id):
        if date and company_id:
            if fields.Date.from_string(date).weekday() == 0:
                return company_id.work_time_monday
            if fields.Date.from_string(date).weekday() == 1:
                return company_id.work_time_tuesday
            if fields.Date.from_string(date).weekday() == 2:
                return company_id.work_time_wednesday
            if fields.Date.from_string(date).weekday() == 3:
                return company_id.work_time_thursday
            if fields.Date.from_string(date).weekday() == 4:
                return company_id.work_time_friday
            if fields.Date.from_string(date).weekday() == 5:
                return company_id.work_time_saturday
            if fields.Date.from_string(date).weekday() == 6:
                return company_id.work_time_sunday

    def calculate_time_between_date(self, date_1, date_2):
        if date_1 and date_2:
            return float((datetime.datetime.strptime(date_1,DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(date_2,DEFAULT_SERVER_DATETIME_FORMAT)).seconds)/ 60 / 60

class hr_attendance_import(models.Model):
    _name           = 'hr.attendance.import'
    _description    = 'Attendance Import'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.attendance.import.sequence.number') or _('New')
        result = super(hr_attendance_import, self).create(vals)
        return result

    name            = fields.Char("Name")
    book            = fields.Binary(string='File Excel')
    book_filename   = fields.Char(string='File Name')
    line_ids        = fields.One2many('hr.attendance', 'import_id', string="Details", )
    company_id      = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())

    def import_attendance(self):
        """
        XL_CELL_EMPTY	0	empty string ‘’
        XL_CELL_TEXT	1	a Unicode string
        XL_CELL_NUMBER	2	float
        XL_CELL_DATE	3	float
        XL_CELL_BOOLEAN	4	int; 1 means True, 0 means False
        XL_CELL_ERROR	5	int representing internal Excel codes; for a text representation, refer to the supplied dictionary error_text_from_code
        XL_CELL_BLANK	6	empty string ‘’. Note: this type will appear only when open_workbook(..., formatting_info= True) is used.
        """
        attendance_obj  = self.env['hr.attendance']
        if not self.book:
            raise exceptions.ValidationError(_("Upload your data first!"))
        if self.line_ids:
            for lines in self.line_ids:
                lines.unlink()
        data        = base64.decodestring(self.book)
        try:
            xlrd.open_workbook(file_contents=data)
        except XLRDError:
            raise exceptions.ValidationError(_("Unsupported Format!"))
        wb          = xlrd.open_workbook(file_contents=data)
        total_sheet = len(wb.sheet_names())
        for i in range(total_sheet):
            sheet       = wb.sheet_by_index(i)
            for rows in range(sheet.nrows):
                #Rows 1 hanya untuk title
                if rows == 0:
                    for j in range(sheet.ncols):
                        if j == 0 and sheet.cell_value(rows, j) <> "Tanggal":
                            raise exceptions.ValidationError(_("Column Title '1 A' must be 'Tanggal'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 1 and sheet.cell_value(rows, j) <> "ID":
                            raise exceptions.ValidationError(_("Column '1 B' must be 'ID'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 2 and sheet.cell_value(rows, j) <> "Nama":
                            raise exceptions.ValidationError(_("Column '1 C' must be 'Nama'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 3 and sheet.cell_value(rows, j) <> "Jam Masuk":
                            raise exceptions.ValidationError(_("Column '1 D' must be 'Jam Masuk'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 4 and sheet.cell_value(rows, j) <> "Jam Istirahat":
                            raise exceptions.ValidationError(_("Column '1 E' must be 'Jam Istirahat'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 5 and sheet.cell_value(rows, j) <> "Jam Masuk Istirahat":
                            raise exceptions.ValidationError(_("Column '1 F' must be 'Jam Masuk Istirahat'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                        if j == 6 and sheet.cell_value(rows, j) <> "Jam Pulang":
                            raise exceptions.ValidationError(_("Column '1 G' must be 'Jam Pulang'! \n Column Title Now : %s \n Error Sheet : %s")%(sheet.cell_value(rows, j), sheet.name))
                else:
                    date            = False
                    employee_id     = False
                    employee_name   = False
                    for k in range(sheet.ncols):
                        if k == 0 and sheet.cell(rows, k).ctype == 3:
                            date        = datetime.datetime(*xlrd.xldate_as_tuple(sheet.cell_value(rows, k), wb.datemode))
                            date        = date.strftime("%Y-%m-%d")
                        else:
                            pass
                        if k == 1 and sheet.cell(rows, k).ctype == 2:
                            employee_ids = self.env['hr.employee'].search([('biometric', '=', int(sheet.cell_value(rows, k)))])
                            if len(employee_ids) > 1:
                                employee_id = employee_ids[-1].id
                            elif len(employee_ids) == 0:
                                pass
                            else:
                                employee_id = employee_ids.id
                        else:
                            pass
                        if k == 2 and sheet.cell(rows, k).ctype == 1:
                            employee_name = str(sheet.cell_value(rows, k))
                        else:
                            pass
                        if k == 3 and sheet.cell(rows, k).ctype == 3:
                            time_check_in   = datetime.time(*(xlrd.xldate_as_tuple(sheet.cell_value(rows, k), wb.datemode))[3:]).strftime(" %H:%M:00")
                            date_check_in   = (datetime.datetime.strptime(date + time_check_in, '%Y-%m-%d %H:%M:%S') - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            pass
                        if k == 4 and sheet.cell(rows, k).ctype == 3:
                            time_rest_out   = datetime.time(*(xlrd.xldate_as_tuple(sheet.cell_value(rows, k), wb.datemode))[3:]).strftime(" %H:%M:00")
                            date_rest_out   = (datetime.datetime.strptime(date + time_rest_out, '%Y-%m-%d %H:%M:%S') - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            pass
                        if k == 5 and sheet.cell(rows, k).ctype == 3:
                            time_rest_in    = datetime.time(*(xlrd.xldate_as_tuple(sheet.cell_value(rows, k), wb.datemode))[3:]).strftime(" %H:%M:00")
                            date_rest_in    = (datetime.datetime.strptime(date + time_rest_in, '%Y-%m-%d %H:%M:%S') - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            pass
                        if k == 6 and sheet.cell(rows, k).ctype == 3:
                            time_check_out  = datetime.time(*(xlrd.xldate_as_tuple(sheet.cell_value(rows, k), wb.datemode))[3:]).strftime(" %H:%M:00")
                            date_check_out  = (datetime.datetime.strptime(date + time_check_out, '%Y-%m-%d %H:%M:%S') - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            pass
                    overtime = 0
                    if (attendance_obj.calculate_time_between_date(date_check_out, date_check_in) - attendance_obj.calculate_time_between_date(date_rest_in, date_rest_out) - attendance_obj.working_day_time(date, self.company_id)) > 0:
                        overtime = (attendance_obj.calculate_time_between_date(date_check_out, date_check_in) - attendance_obj.calculate_time_between_date(date_rest_in, date_rest_out) - attendance_obj.working_day_time(date, self.company_id))
                    if employee_id:
                        attendance_obj.create({
                            'import_id'     : self.id,
                            'employee_id'   : employee_id,
                            'check_in'      : date_check_in,
                            'rest_out'      : date_rest_out,
                            'rest_in'       : date_rest_in,
                            'check_out'     : date_check_out,
                            'total_time'    : attendance_obj.calculate_time_between_date(date_check_out, date_check_in),
                            'rest_time'     : attendance_obj.calculate_time_between_date(date_rest_in, date_rest_out),
                            'working_time'  : attendance_obj.calculate_time_between_date(date_check_out, date_check_in) - attendance_obj.calculate_time_between_date(date_rest_in, date_rest_out),
                            'work_day_time' : attendance_obj.working_day_time(date, self.company_id),
                            'overtime'      : overtime,
                        })

        return True #untuk keperluan debug