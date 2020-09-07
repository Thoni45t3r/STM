# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import time
import datetime
from dateutil.relativedelta import relativedelta

class hr_minimum_wage(models.Model):
    _inherit        = 'hr.minimum.wage'
    _description    = 'C10i Minimum Wage Management Inherit Plantation'

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


class hr_foreman_movement(models.Model):
    _name           = 'hr.foreman.movement'
    _description    = 'Plantation Moving Employee'

    name                = fields.Char("Name")
    date                = fields.Date("Tanggal Pengajuan Pindah")
    moved_date          = fields.Date("Tanggal Pindah")
    employee_id         = fields.Many2one(comodel_name="hr.employee", string="Karyawan", ondelete="restrict")
    src_foreman_id      = fields.Many2one(comodel_name="hr.foreman", string="Kemandoran Asal", ondelete="restrict")
    dest_foreman_id     = fields.Many2one(comodel_name="hr.foreman", string="Kemandoran Tujuan", ondelete="restrict")
    note                = fields.Text("Catatan")
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', default=lambda self: self.env.user)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state               = fields.Selection(selection=[('cancel','Dibatalkan'),('ongoing','Dalam Proses'),('moved','Sudah Pindah')], string='Status', default='ongoing', readonly=True)

    @api.model
    def cron_move_employee(self):
        self.scheduler_auto_move_employee()

    @api.model
    def scheduler_auto_move_employee(self):
        all_movement_ids = self.search([('state', '=', 'ongoing')])
        if all_movement_ids:
            for move in all_movement_ids:
                if move.employee_id:
                    move.employee_id.write({'kemandoran_id' : move.dest_foreman_id.id,
                                            'move_state'    : 'moved'})
                    move.write({'state'         : 'moved',
                                'moved_date'    : datetime.datetime.now().strftime('%Y-%m-%d')})

class hr_foreman(models.Model):
    _name           = 'hr.foreman'
    _description    = 'Master Data Kemandoran'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    foreman_id_1    = fields.Many2one(comodel_name="hr.employee", string="Mandor 1", ondelete="restrict")
    foreman_id      = fields.Many2one(comodel_name="hr.employee", string="Mandor", ondelete="restrict")
    admin_id_1      = fields.Many2one(comodel_name="hr.employee", string="Kerani 1", ondelete="restrict")
    admin_id        = fields.Many2one(comodel_name="hr.employee", string="Kerani", ondelete="restrict")
    nik_mandor_1    = fields.Char("NIK Mandor 1", related='foreman_id_1.no_induk', readonly=True)
    nik_mandor      = fields.Char("NIK Mandor", related='foreman_id.no_induk', readonly=True)
    nik_kerani_1    = fields.Char("NIK Kerani", related='admin_id_1.no_induk', readonly=True)
    nik_kerani      = fields.Char("NIK Kerani", related='admin_id.no_induk', readonly=True)
    user_input_id   = fields.Many2one(comodel_name="res.users", string="Kerani Inputer")
    active          = fields.Boolean("Active", default=True)
    afdeling_id     = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    department_id   = fields.Many2one(comodel_name="hr.department", string="Departemen", ondelete="restrict")
    division_id     = fields.Many2one(comodel_name="hr.division", string="Divisi", ondelete="restrict")
    notes           = fields.Text("Catatan")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    employee_ids    = fields.One2many('hr.employee', 'kemandoran_id', string="Daftar Karyawan", )

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

class hr_employee_status(models.Model):
    _name           = 'hr.employee.status'
    _description    = 'Employee Status'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    active          = fields.Boolean("Active", default=True)
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

class hr_employee_foreman_transfer(models.Model):
    _name           = 'hr.employee.foreman.transfer'
    _description    = 'Daftar Transfer Kemandoran'

    name                = fields.Char("LHM Name")
    date                = fields.Date("Tanggal")
    lhm_id              = fields.Many2one(comodel_name="lhm.transaction", string="LHM")
    lhm_line_id         = fields.Many2one(comodel_name="lhm.transaction.line", string="LHM Line")
    other_lhm_id        = fields.Many2one(comodel_name="lhm.transaction", string="Other LHM")
    other_lhm_line_id   = fields.Many2one(comodel_name="lhm.transaction.line", string="Other LHM Line")
    employee_id         = fields.Many2one(comodel_name="hr.employee", string="Nama Karyawan", ondelete="restrict")
    kemandoran_from_id  = fields.Many2one(comodel_name="hr.foreman", string="Asal Kemandoran")
    kemandoran_to_id    = fields.Many2one(comodel_name="hr.foreman", string="Tujuan Kemandoran")
    type                = fields.Selection([('in', 'Masuk'), ('out', 'Keluar')], string='Type')


class hr_attendance_type(models.Model):
    _name           = 'hr.attendance.type'
    _description    = 'Employee Attendance Type'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    special         = fields.Boolean("Spesial")
    type            = fields.Selection([('in', 'Masuk'), ('out', 'Keluar'), ('na', 'N/A'), ('kj', 'KJ')], string='Type')
    type_hk         = fields.Selection([('hke', 'HKE'), ('hkne', 'HKNE')], string='HK Type')
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active          = fields.Boolean("Active", default=True)

    @api.onchange('special')
    def _onchange_special(self):
        if self.special:
            pass
        else:
            self.type = False

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
        hr_attendance_type = self.search(domain + args, limit=limit)
        return hr_attendance_type._name_get()

class hr_employee_type(models.Model):
    _name           = 'hr.employee.type'
    _description    = 'Employee Type'

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    status_id           = fields.Many2one(comodel_name="hr.employee.status", string="Status", ondelete="restrict")
    sequence_id         = fields.Many2one(comodel_name="ir.sequence", string="Sequence", ondelete="restrict")
    overtime_calc       = fields.Boolean("Calculate Overtime", default=False)
    monthly_employee    = fields.Boolean("Monthly Employee", default=False)
    sku_employee        = fields.Boolean("SKU Employee", default=False)
    bhl_employee        = fields.Boolean("BHL Employee", default=False)
    contract_employee   = fields.Boolean("Contract Employee", default=False)
    other_employee      = fields.Boolean("Other Employee", default=False)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active              = fields.Boolean("Active", default=True)
    umr_ids             = fields.One2many(comodel_name="hr.minimum.wage", inverse_name="employee_type_id", string="History UMR")

class hr_sub_department(models.Model):
    _name           = 'hr.sub.department'
    _description    = 'Employee Sub Departemen'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active          = fields.Boolean("Active", default=True)

class hr_division(models.Model):
    _name           = 'hr.division'
    _description    = 'Employee Division'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active          = fields.Boolean("Active", default=True)

class hr_job(models.Model):
    _inherit        = 'hr.job'
    _description    = 'HR Jobs LHM'

    is_lhm              = fields.Boolean("Data LHM")
    active              = fields.Boolean("Active", default=True)

    _sql_constraints = [('name_company_uniq', 'CHECK(1=1)', 'Nama Jabatan tidak boleh sama!'),]

class hr_department(models.Model):
    _inherit        = 'hr.department'
    _description    = 'HR Department LHM'

    is_lhm          = fields.Boolean("Data LHM")

class hr_employee(models.Model):
    _inherit        = 'hr.employee'
    _description    = 'Employee'
    # _rec_name       = 'name'

    def _default_religion(self):
        religion = self.env['hr.employee.religion'].search([])[-1]
        return religion and religion.id or False

    def _default_ptkp(self):
        ptkp = self.env['hr.ptkp'].search([('marital','=','TK')])[-1]
        return ptkp and ptkp.id or False

    #####################################
    # Override from c10i_hr
    #####################################
    no_induk            = fields.Char('NIK', default="/")
    gender              = fields.Selection([
                            ('Laki-laki', 'Laki-laki'),
                            ('Perempuan', 'Perempuan'),
                            ('Lainnya', 'Lainnya')
                        ], default="Lainnya", string='Jenis Kelamin', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    marital             = fields.Selection([
                            ('TK', 'Tidak Menikah'),
                            ('K', 'Menikah'),
                        ], default="TK", string='Status Pernikahan', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    ptkp_id             = fields.Many2one(comodel_name='hr.ptkp', string="PTKP", default=_default_ptkp)
    religion            = fields.Many2one(comodel_name='hr.employee.religion', string="Agama", default=_default_religion)
    #####################################
    # Override from hr
    #####################################
    birthday            = fields.Date('Date of Birth', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee', default=lambda self: fields.Datetime.now())
    identification_id   = fields.Char(string='Identification No', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    passport_id         = fields.Char('Passport No', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    bank_account_id     = fields.Many2one('res.partner.bank', string='Bank Account Number', domain="[('partner_id', '=', address_home_id)]", help='Employee bank salary account', groups='hr.group_hr_user,c10i_lhm.group_plantation_super,c10i_lhm.group_plantation_operator_employee')
    #####################################
    # Override from hr_contract
    #####################################
    place_of_birth  = fields.Char('Place of Birth', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    children            = fields.Integer(string='Number of Children', groups='hr.group_hr_user,c10i_lhm.group_plantation_supervisor,c10i_lhm.group_plantation_operator_employee')
    #####################################
    contract_type       = fields.Many2one(comodel_name='hr.contract.type', string='Jenis Kontrak', ondelete="restrict")
    start_date_contract = fields.Date(string="Mulai Kontrak")
    end_date_contract   = fields.Date(string="Selesai Kontrak")
    mandor              = fields.Boolean("Mandor", help="Centang jika dia adalah mandor")
    kerani              = fields.Boolean("Kerani", help="Centang jika dia adalah kerani")
    is_lhm              = fields.Boolean("LHM", help="Data Karyawan LHM")
    is_npwp             = fields.Boolean("NPWP", help="Have NPWP")
    kesehatan           = fields.Boolean("Kesehatan", help="Have BPJS Kesehatan")
    bpjs_kes_date_start = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan BPJS Kesehatan")
    # bpjs_kes_date_end   = fields.Date("Tanggal Berakhir", help="Tanggal Daftar dan mulai dikenakan BPJS")
    ketenagakerjaan     = fields.Boolean("Ketenagakerjaan", help="Have BPJS Ketenagakerjaan")
    bpjs_tk_date_start  = fields.Date("Tanggal Daftar", help="Tanggal Daftar dan mulai dikenakan BPJS Ketenagakerjaan")
    sub_department_id   = fields.Many2one(comodel_name="hr.sub.department", string="Pangkat", ondelete="restrict")
    type_id             = fields.Many2one(comodel_name="hr.employee.type", string='Tipe Karyawan', ondelete="restrict")
    afdeling_id         = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    cost_center_id      = fields.Many2one(comodel_name="account.cost.center", string="Cost Center", ondelete="restrict")
    division_id         = fields.Many2one(comodel_name="hr.division", string="Divisi", ondelete="restrict")
    custom_nik          = fields.Boolean("NIK Manual")
    auto_generate       = fields.Boolean("NIK Automatic")
    noedit_foreman      = fields.Boolean("No Edit Foreman")
    appointment_date    = fields.Date("Tanggal Pengangkatan")
    work_start_date     = fields.Date("Tanggal Masuk")
    work_end_date       = fields.Date("Tanggal Keluar")
    basic_salary_type   = fields.Selection(selection=[('employee','Karyawan'), ('employee_type','Tipe Karyawan')], string="Acuan Gaji Pokok", default="employee_type")
    kemandoran_id       = fields.Many2one(comodel_name='hr.foreman', string='Kemandoran', ondelete="restrict")
    mandor_id           = fields.Many2one(comodel_name="hr.employee", string="Mandor", ondelete="restrict", related='kemandoran_id.foreman_id', readonly=True)
    move_state          = fields.Selection(selection=[('cancel','Dibatalkan'),('ongoing','Dalam Proses'),('moved','Sudah Pindah')], string='Move Status', readonly=True)
    movement_ids        = fields.One2many(comodel_name="hr.foreman.movement", inverse_name="employee_id", string="History Movement")
    umr_ids             = fields.One2many(comodel_name="hr.minimum.wage", inverse_name="employee_id", string="History UMR")
    plantation_location_type_id = fields.Many2one('lhm.location.type', 'Tipe Lokasi')
    plantation_location_id = fields.Many2one('lhm.location', 'Lokasi')
    plantation_activity_hkne_id = fields.Many2one('lhm.activity', 'HKNE')
    plantation_activity_natura_id = fields.Many2one('lhm.activity', 'Natura')
    plantation_activity_bpjs_tk_id = fields.Many2one('lhm.activity', 'BPJS Tenaga Kerja')
    plantation_activity_bpjs_kes_id = fields.Many2one('lhm.activity', 'BPJS Kesehatan')

    @api.onchange('kemandoran_id')
    def onchange_kemandoran_id(self):
        if self.kemandoran_id.division_id or self.kemandoran_id.afdeling_id:
            self.division_id = self.kemandoran_id.division_id
            self.afdeling_id = self.kemandoran_id.afdeling_id

    @api.onchange('ketenagakerjaan')
    def onchange_ketenagakerjaan(self):
        if self.ketenagakerjaan:
            self.bpjs_tk_date_start = time.strftime('%Y-%m-%d')
        else:
            self.bpjs_tk_date_start = False
    
    @api.onchange('kesehatan')
    def onchange_kesehatan(self):
        if self.kesehatan:
            self.bpjs_kes_date_start = time.strftime('%Y-%m-%d')
        else:
            self.bpjs_kes_date_start = False

    @api.model
    def create(self, values):
        if values.get('type_id', False) and not values.get('custom_nik', False):
            employee_type   = self.env['hr.employee.type'].browse(values['type_id'])
            sequence_id     = employee_type and employee_type.sequence_id or False
            if sequence_id:
                sequence_number         = sequence_id.next_by_id()
                values['no_induk']      = sequence_number
                values['auto_generate'] = True
        values['noedit_foreman'] = True
        employee = super(hr_employee, self).create(values)
        return employee

    @api.multi
    def write(self, values):
        if values.get('custom_nik', self.custom_nik):
            pass
        else:
            if values.get('type_id', self.type_id):
                employee_type = self.env['hr.employee.type'].browse(values.get('type_id', self.type_id.id))
                sequence_id = employee_type and employee_type.sequence_id or False
                if sequence_id:
                    if self.type_id.sequence_id.id == sequence_id.id:
                        values['auto_generate'] = True
                    else:
                        sequence_number         = sequence_id.next_by_id()
                        values['no_induk']      = sequence_number
                        values['auto_generate'] = True
        res = super(hr_employee, self).write(values)
        return res