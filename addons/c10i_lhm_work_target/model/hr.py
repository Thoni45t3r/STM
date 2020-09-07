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
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
TAHUN = [(num, str(num)) for num in range((datetime.now().year) - 30, (datetime.now().year) + 1)]

class hr_insurance(models.Model):
    _inherit = 'hr.insurance'

    employee_type_id = fields.Many2one('hr.employee.type', 'Tipe Karyawan')

class hr_minimum_wage(models.Model):
    _inherit        = 'hr.minimum.wage'

    rate_panen_ids = fields.One2many('hr.minimum.wage.rate.panen', 'min_wage_id', 'Rate Panen')
    rate_rawat_ids = fields.One2many('hr.minimum.wage.rate.rawat', 'min_wage_id', 'Rate Rawat')
    activity_id = fields.Many2one('lhm.activity', 'Force Activity')

    @api.model
    def default_get(self, fields):
        res = super(hr_minimum_wage, self).default_get(fields)

        block_year_group = self.env['lhm.plant.block'].read_group([('id','>',0)], ['year'], ['year'])
        block_year = [x['year'] for x in block_year_group]
        default_rate_panen = map(lambda x:(0,0,{'year':x, 'rate':0.0}), block_year)
        if 'rate_panen_ids' in fields:
            res.update({'rate_panen_ids': default_rate_panen})
        
        default_rate_rawat = map(lambda x:(0,0,{'year': x, 'rate': 0.0}), block_year)
        if 'rate_rawat_ids' in fields:
            res.update({'rate_rawat_ids': default_rate_rawat})
        return res

    @api.multi
    def get_rate_panen(self, tahun_tanam, uom_id=None):
        self.ensure_one()
        if uom_id is None:
            rate = self.env['hr.minimum.wage.rate.panen'].search([('year','=',tahun_tanam),('min_wage_id','=',self.id)])
        else:
            rate = self.env['hr.minimum.wage.rate.panen'].search([('year','=',tahun_tanam),('min_wage_id','=',self.id),('uom_id','=',uom_id)])

        if not rate:
            raise UserError(_('Rate Panen Tahun %s belum didefinisikan pada Master UMR %s')%(str(tahun_tanam), self.name))
        return rate[-1].rate

    @api.multi
    def get_rate_rawat(self, tahun_tanam, uom_id=None):
        self.ensure_one()
        if uom_id is None:
            rate = self.env['hr.minimum.wage.rate.rawat'].search([('year','=',tahun_tanam),('min_wage_id','=',self.id)])
        else:
            rate = self.env['hr.minimum.wage.rate.rawat'].search([('year','=',tahun_tanam),('min_wage_id','=',self.id),('uom_id','=',uom_id)])
    
        if not rate:
            raise UserError(_('Rate Rawat %s belum didefinisikan pada Master UMR %s')%(str(tahun_tanam), self.name))
        return rate[-1].rate

    @api.onchange('year', 'date_from', 'date_to', 'employee_id', 'employee_type_id', 'basic_salary_type', 'activity_id')
    def onchange_date_and_year(self):
        # domain  = [('id', '!=', self._origin.id), ('year', '=', self.year), ('basic_salary_type', '=', False)]

        if not self.date_from or not self.date_to:
            return {}

        if self.date_from > self.date_to:
            self.date_to = self.date_from
            return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Tanggal Berakhir Harus Lebih Besar dari Tanggal Mulai")},
                }

        # domain = [('id', '!=', self._origin.id), ('date_from', '>=', self.date_from)]
        domain = [('id', '!=', self._origin.id)]
        if self.activity_id:
            domain.append(('activity_id', '=', self.activity_id.id))
        else:
            domain.append(('activity_id', '=', False))

        if self.basic_salary_type and self.basic_salary_type=='employee' and self.employee_id:
            self.employee_type_id = False
            domain.append(('employee_id', '=', self.employee_id.id))
        else:
            domain.append(('employee_id', '=', False))
        
        if self.basic_salary_type and self.basic_salary_type=='employee_type' and self.employee_type_id:
            self.employee_id = False
            domain.append(('employee_type_id', '=', self.employee_type_id.id))
        else:
            domain.append(('employee_type_id', '=', False))

        # Validasi UMR yg sama jika tanggal berakhir-nya sudah didefinisikan ditempat lain
        check = self.env['hr.minimum.wage'].search(domain+[('date_to','>=',self.date_from)], order="date_to asc")
        if check:
            self.date_from = False
            self.date_to = False
            return {
                    'warning': {'title': _('Invalid Data Input'),
                        'message': _("UMR ini sudah didefinisikan pada %s dengan durasi antara %s s.d %s \n\
                        Silahkan diubah terlebih dahulu untuk membuat durasi UMR baru")% \
                        (check[-1].name, check[-1].date_from, check[-1].date_to)
                        },
                    }

class hr_minumum_wage_rate_panen(models.Model):
    _name = 'hr.minimum.wage.rate.panen'
    
    min_wage_id = fields.Many2one('hr.minimum.wage', 'Minimum Wage')
    year = fields.Selection(TAHUN, 'Tahun Tanam', required=True)
    rate = fields.Float('Rate/(Kg)', required=True)
    uom_id = fields.Many2one('product.uom', 'Satuan')

class hr_minumum_wage_rate_rawat(models.Model):
    _name = 'hr.minimum.wage.rate.rawat'
    
    min_wage_id = fields.Many2one('hr.minimum.wage', 'Minimum Wage')
    year = fields.Selection(TAHUN, 'Tahun Tanam', required=True)
    rate = fields.Float('Rate', required=True)
    uom_id = fields.Many2one('product.uom', 'Satuan')


class hr_employee_type(models.Model):
    _inherit        = 'hr.employee.type'
    _description    = 'Employee Type'

    #New Fields
    pkwt_employee   = fields.Boolean("PKWT Employee", default=False)


class hr_employee(models.Model):
    _inherit        = 'hr.employee'
    _description    = 'C10i Employee Management'

    #New Fields
    pensiun          = fields.Boolean('Pensiun')
