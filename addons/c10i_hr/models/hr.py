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

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class hr_employee(models.Model):
    _inherit        = 'hr.employee'
    _description    = 'Employee Management'

    #Override From HR base Odoo
    work_phone      = fields.Char('No. Telephone', related='address_id.phone', readonly=True)
    mobile_phone    = fields.Char('No. Handphone', related='address_id.mobile', readonly=True)
    work_email      = fields.Char('Alamat Email', related='address_id.email', readonly=True)
    work_location   = fields.Char('Lokasi Pekerjaan')
    gender          = fields.Selection([
                        ('Laki-laki', 'Laki-laki'),
                        ('Perempuan', 'Perempuan'),
                        ('Lainnya', 'Lainnya')
                        ], string='Jenis Kelamin', groups='hr.group_hr_user')
    marital         = fields.Selection([
                        ('TK', 'Tidak Menikah'),
                        ('K', 'Menikah'),
                        ], string='Status Pernikahan', groups='hr.group_hr_user')

    #New Fields
    street                  = fields.Char(string="Alamat 1")
    street2                 = fields.Char(string="Alamat 2")
    zip                     = fields.Char(string="Kode Pos")
    city_id                 = fields.Many2one('res.state.city', 'Kota/ Kabupaten', domain="[('state_id', '=', state_id),('country_id', '=', country_id)]")
    state_id                = fields.Many2one('res.country.state', 'Provinsi', domain="[('country_id', '=', country_id)]")
    country_id              = fields.Many2one('res.country', 'Negara')
    nationality_id          = fields.Many2one('res.country', 'Kewarganegaraan')
    no_induk                = fields.Char('NIK',)
    npwp                    = fields.Char('NPWP', )
    bpjs_kesehatan          = fields.Char('BPJS Kesehatan', )
    bpjs_ketenagakerjaan    = fields.Char('BPJS Ketenagakerjaan', )
    ptkp_id                 = fields.Many2one(comodel_name='hr.ptkp', string="PTKP", track_visibility='onchange')
    religion                = fields.Many2one(comodel_name='hr.employee.religion', string="Agama")
    education_ids           = fields.One2many('hr.employee.education.line','employee_id', string="Jenjang Pendidikan", )
    license_ids             = fields.One2many('hr.employee.driving.license.line', 'employee_id', string="SIM", )
    experinece_ids          = fields.One2many('hr.employee.experience.line', 'employee_id', string="Pengalaman Kerja", )
    ptkp_history_ids        = fields.One2many('hr.ptkp.history', 'employee_id', string="PTKP History", )

    @api.model
    def create(self, values):
        res =super(hr_employee, self).create(values)
        if res.ptkp_id:
            self.env['hr.ptkp.history'].create({
                'name'          : res.name,
                'employee_id'   : res.id,
                'ptkp_id'       : res.ptkp_id and res.ptkp_id.id,
                'date'          : datetime.datetime.now().strftime('%Y-%m-%d')
            })
        return res

    @api.multi
    def write(self, values):
        if values.get('ptkp_id'):
            self.env['hr.ptkp.history'].create({
                'name'          : self.name,
                'employee_id'   : self.id,
                'ptkp_id'       : self.ptkp_id and self.ptkp_id.id,
                'date'          : datetime.datetime.now().strftime('%Y-%m-%d')
            })
        return super(hr_employee, self).write(values)

####################################################### Master Overtime ########################################################
class hr_overtime(models.Model):
    _name           = 'hr.overtime'
    _description    = 'C10i Overtime Management'

    name        = fields.Char("Nama", )
    hours       = fields.Float("Jam")
    normal_day  = fields.Float("Hari Biasa")
    holiday     = fields.Float("Hari Libur")
    work_hours  = fields.Float("Jam Kerja", default=173)
    company_id  = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    active      = fields.Boolean('Aktif', required=True, default=True)

    @api.model
    def create(self, values):
        values['name'] = "OVT/" + (self.env.user.company_id.name or "") + "-" + (str(values.get('hours') or ""))
        return super(hr_overtime, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('hours'):
            values['name'] = "OVT/" + (self.env.user.company_id.name or "") + "-" + (str(values.get('hours') or ""))
        return super(hr_overtime, self).write(values)
#################################################### End Of Master Overtime ####################################################

####################################################### Master Nature ########################################################
class hr_nature(models.Model):
    _name           = 'hr.nature'
    _description    = 'C10i Nature Management'

    @api.depends('ptkp_id')
    def _compute_married(self):
        for nature in self:
            if nature.ptkp_id.marital == 'K':
                nature.married = True
            elif nature.ptkp_id.marital == 'TK':
                nature.married = False
            else:
                nature.married = False

    @api.depends('nature', 'weight', 'weight_married', 'weight_children', 'children')
    def _compute_value_kg(self):
        for nature in self:
            if nature.nature != 0 and nature.weight != 0:
                nature.value_rp = nature.nature / (nature.weight + nature.weight_married + (nature.weight_children * nature.children))

    @api.depends('nature', 'weight', 'weight_married', 'weight_children', 'potongan_kg', 'children')
    def _compute_potongan_kg(self):
        for nature in self:
            if nature.nature != 0 and nature.weight != 0:
                nature.potongan_rp = (nature.nature / (nature.weight + nature.weight_married + (nature.weight_children * nature.children))) * nature.potongan_kg

    name            = fields.Char("Nama", )
    ptkp_id         = fields.Many2one(comodel_name='hr.ptkp', string="PTKP")
    nature          = fields.Float("Natura")
    weight          = fields.Float("Tunjangan Pribadi(Kg)")
    weight_married  = fields.Float("Tunjangan Nikah(Kg)")
    weight_children = fields.Float("Tunjangan Anak(Kg)")
    potongan_kg     = fields.Float("Potongan(Kg)")
    married         = fields.Boolean("Nikah", compute=_compute_married, store=True)
    children        = fields.Integer(string="Jumlah Anak", related="ptkp_id.children", store=True)
    value_rp        = fields.Float("Per Kg(Rp)", compute=_compute_value_kg, store=True)
    potongan_rp     = fields.Float("Potongan(Rp)", compute=_compute_potongan_kg, store=True)
    company_id      = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    active          = fields.Boolean('Aktif', required=True, default=True)
#################################################### End Of Master Nature ####################################################

class hr_minimum_wage(models.Model):
    _name           = 'hr.minimum.wage'
    _description    = 'C10i Minimum Wage Management'
    _order          = 'year desc,date_to desc'

    @api.model
    def _get_state(self):
        for state in self:
            all_umr     = self.env['hr.minimum.wage'].search([('id', '!=', state.id), ('year','=',state.year), ('date_to','>',state.date_to)])
            if all_umr:
                state.state = 'notactive'
            else:
                state.state = 'active'

    def _default_year(self):
        return int(time.strftime('%Y'))

    name        = fields.Char('Nama', required=False, default="_(NEW)_UMR")
    year        = fields.Selection([(num, str(num)) for num in range((datetime.datetime.now().year)-10, (datetime.datetime.now().year)+2 )], string='Tahun', default=_default_year)
    umr_month   = fields.Float(string="UMR(Bulan)")
    date_from   = fields.Date("Tanggal Mulai")
    date_to     = fields.Date("Tanggal Berakhir")
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state       = fields.Selection([('active', 'Active'), ('notactive', 'Not Active')], string='Status', compute=_get_state)

    @api.onchange('year','date_from','date_to')
    def onchange_date_and_year(self):
        other_ids   = self.env['hr.minimum.wage'].search([('id','!=',self._origin.id),('year','=',self.year)], order="date_to asc")
        if other_ids:
            other_ids = other_ids[-1] #<--- mengambil tanggal akhir paling besar
        else:
            other_ids = False
        if self.date_to:
            if self.date_to and self.date_to <= self.date_from:
                res = {}
                self.date_to = fields.Date.from_string(self.date_from) + relativedelta(days=1)
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Tanggal Berakhir Harus Lebih Besar dari Tanggal Mulai")},
                }
            elif int(fields.Date.from_string(self.date_to).strftime('%Y')) != self.year:
                res             = {}
                res['warning']  = {'title': _('Kesalahan Input Data'),
                                    'message': _("Tanggal %s tidak dalam tahun: %s.") % (self.date_to, self.year)}
                self.date_to    = time.strftime(str(self.year) + '-12-31')
                return res
        elif self.year:
            if other_ids and other_ids.date_to == time.strftime(str(self.year) + '-12-31'):
                res             = {}
                res['warning']  = {'title': _('Kesalahan Input Data'),
                                    'message': _("Semua range tanggal pada tahun %s sudah didefinisikan") % self.year}
                self.year       = False
                return res
            elif self.year and other_ids:
                res = {}
                self.date_from  = fields.Date.from_string(other_ids.date_to) + relativedelta(days=1)
                self.date_to    = time.strftime(str(self.year) + '-12-31')
            else:
                res = {}
                self.date_from  = time.strftime(str(self.year) + '-01-01')
                self.date_to    = time.strftime(str(self.year) + '-12-31')

    @api.model
    def create(self, values):
        if values.get('umr_month') <= 0.0:
            raise ValidationError("UMR harus lebih dari 0")
        return super(hr_minimum_wage, self).create(values)

    @api.multi
    def write(self, values):
        if isinstance(values.get('umr_month', False), bool) == False:
            if values.get('umr_month') <= 0.0:
                raise ValidationError("UMR harus lebih dari 0")
        return super(hr_minimum_wage, self).write(values)

    @api.multi
    def unlink(self):
        for umr in self:
            if umr.state != 'active':
                raise UserError(_('Dokumen tidak dapat dihapus jika status bukan Aktif'))
        min_wage = super(hr_minimum_wage, self).unlink()
        return min_wage

class hr_insurance(models.Model):
    _name           = 'hr.insurance'
    _description    = 'C10i Insurance Management'

    name        = fields.Char('Nama', required=False)
    type        = fields.Selection([
                        ('kesehatan', 'Kesehatan'),
                        ('ketenagakerjaan', 'Ketenagakerjaan'),
                        ('pensiun', 'Pensiun'),
                        ('other', 'Lain-lain'),
                        ], string='Tipe Asuransi', default="kesehatan")
    potongan    = fields.Float(string="Tarif(%)")
    tunjangan   = fields.Float(string="Tunjangan(%)")
    date_from   = fields.Date("Tanggal Mulai")
    date_to     = fields.Date("Tanggal Berakhir")
    old_id      = fields.Many2one('hr.insurance', string='Asuransi Sebelumnya')
    company_id  = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    active      = fields.Boolean('Aktif', required=True, default=True)
    setoran_account_id = fields.Many2one('account.account', 'Setoran Account')
    tunjangan_account_id = fields.Many2one('account.account', 'Tunjangan Account')

    @api.onchange('type')
    def _onchange_type(self):
        self.old_id = False
        if self.type == 'kesehatan':
            insurance_data  = self.env['hr.insurance'].search([('type', '=', 'kesehatan') ,('active','=',True)], order="date_to desc", limit=1)
            if insurance_data:
                date_from       = fields.Date.from_string(insurance_data.date_to) + relativedelta(days=1)
                self.date_from  = date_from
                self.old_id     = insurance_data.id
        elif self.type == 'ketenagakerjaan':
            insurance_data  = self.env['hr.insurance'].search([('type', '=', 'ketenagakerjaan') ,('active','=',True)], order="date_to desc", limit=1)
            if insurance_data:
                date_from       = fields.Date.from_string(insurance_data.date_to) + relativedelta(days=1)
                self.date_from  = date_from
                self.old_id     = insurance_data.id
        elif self.type == 'pensiun':
            insurance_data  = self.env['hr.insurance'].search([('type', '=', 'pensiun') ,('active','=',True)], order="date_to desc", limit=1)
            if insurance_data:
                date_from       = fields.Date.from_string(insurance_data.date_to) + relativedelta(days=1)
                self.date_from  = date_from
                self.old_id     = insurance_data.id

    @api.model
    def create(self, values):
        if values.get('date_to') <= values.get('date_from'):
            raise ValidationError("Tanggal berakhir tidak boleh lebih kecil atau sama dengan tanggal awal")

        if values.get('type') == 'kesehatan':
            values['name'] = self.env['ir.sequence'].next_by_code('hr.insurance.kesehatan.sequence.number')
        elif values.get('type') == 'ketenagakerjaan':
            values['name'] = self.env['ir.sequence'].next_by_code('hr.insurance.ketenagakerjaan.sequence.number')
        elif values.get('type') == 'pensiun':
            values['name'] = self.env['ir.sequence'].next_by_code('hr.insurance.pensiun.sequence.number')
        else:
            values['name'] = "Lain - Lain"
        return super(hr_insurance, self).create(values)

class hr_ptkp(models.Model):
    _name           = 'hr.ptkp'
    _description    = 'C10i PTKP Management'

    name            = fields.Char('Status', required=True)
    code            = fields.Char('Kode', required=True)
    marital         = fields.Selection([
                        ('TK', 'Tidak Menikah'),
                        ('K', 'Menikah'),
                        ], string='Status Pernikahan')
    children        = fields.Integer('Jumlah Anak')
    value           = fields.Float('Nilai', required=True)
    company_id      = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    active          = fields.Boolean('Aktif', required=True, default=True)

class hr_ptkp_history(models.Model):
    _name           = 'hr.ptkp.history'
    _description    = 'C10i PTKP History'

    name            = fields.Char('Status', required=True)
    ptkp_id         = fields.Many2one('hr.ptkp', string='PTKP')
    employee_id     = fields.Many2one('hr.employee', string='Employee')
    date            = fields.Date("Change Date")
    company_id      = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())

class hr_employee_religion(models.Model):
    _name           = 'hr.employee.religion'
    _description    = 'C10i Religion Management'

    name            = fields.Char('Agama', required=True)
    company_id      = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    active          = fields.Boolean('Aktif', required=True, default=True)

class hr_employee_education_line(models.Model):
    _name           = 'hr.employee.education.line'
    _description    = 'C10i Education Information'

    name            = fields.Char('Nama Sekolah', required=True)
    level           = fields.Selection([
                        ('Tidak Sekolah', 'Tidak Sekolah'),
                        ('TK', 'TK'),
                        ('SD', 'SD/MI'),
                        ('SMP', 'SMP/MTs'),
                        ('SMA', 'SMA/SMK/MA'),
                        ('D3', 'D3'),
                        ('D4', 'D4'),
                        ('S1', 'S1'),
                        ('S2', 'S2'),
                        ('S3', 'S3'),
                        ], string='Jenjang Pendidikan', required=True)
    major           = fields.Char('Jurusan', required=False)
    start_year      = fields.Selection([(num, str(num)) for num in range(1900, (datetime.datetime.now().year)+1 )], 'Tahun Masuk')
    end_year        = fields.Selection([(num, str(num)) for num in range(1900, (datetime.datetime.now().year)+1 )], 'Tahun Lulus')
    note            = fields.Char('Catatan', required=False)
    employee_id     = fields.Many2one(comodel_name="hr.employee", string="Employee")

class hr_employee_driving_license_line(models.Model):
    _name           = 'hr.employee.driving.license.line'
    _description    = 'C10i Driving Licence Information'

    name            = fields.Char('No. SIM', required=True)
    license_type    = fields.Selection([
                            ('SIM A', 'SIM A'),
                            ('SIM B1', 'SIM B1'),
                            ('SIM B2', 'SIM B2'),
                            ('SIM C', 'SIM C'),
                            ('SIM D', 'SIM D'),
                        ], string='Jenis SIM', required=True)
    expiry_date     = fields.Date("Tanggal Kadaluarsa")
    note            = fields.Char('Catatan', required=False)
    employee_id     = fields.Many2one(comodel_name="hr.employee", string="Employee")


class hr_employee_experience_line(models.Model):
    _name           = 'hr.employee.experience.line'
    _description    = 'C10i Experience Information'

    name            = fields.Char('Nama Perusahaan', required=True)
    job_name        = fields.Char("Nama Pekerjaan", required=True)
    start_date      = fields.Date("Tanggal Mulai")
    end_date        = fields.Date("Tanggal Selasai")
    note            = fields.Char("Catatan", required=False)
    employee_id     = fields.Many2one(comodel_name="hr.employee", string="Employee")