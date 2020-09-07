# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo.tools.translate import _
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class lhm_transaction(models.Model):
    _inherit = 'lhm.transaction'

    lhm_input_type = fields.Selection([('reguler','Reguler'),('work_target','Target Pekerjaan')], 'Transaction Type', default=lambda self: self.env.context.get('lhm_input_type','reguler'))
    nab_allocated = fields.Boolean('NAB Allocated')

    @api.multi
    def button_draft(self):
        for lhm in self:
            if lhm.lhm_input_type=='work_target':
                for line in lhm.lhm_line_ids:
                    if line.activity_id.is_panen and line.lhm_nab_ids:
                        raise ValidationError(_("LHM %s sudah terhubung dengan NAB (%s). \
                            Silahkan Cancel NAB terlebih dahulu sebelum Set Draft LHM")%(lhm.name, \
                            ",".join(line.lhm_nab_ids.mapped('nab_id.name'))))
        return super(lhm_transaction, self).button_draft()

    @api.multi
    def update_salary_based_on_target(self):
        for lhm in self.filtered(lambda x: x.lhm_input_type=='work_target'):
            for line in lhm.lhm_line_ids.filtered(lambda x: x.activity_id.is_panen==True and x.attendance_id.type in ('kj','na')):
                if line.dummy_skip:
                    continue
                wage_value = 0.0
                penalty_nab = 0.0
                if line.lhm_nab_ids:
                    for nab_link in line.lhm_nab_ids:
                        wage_value += nab_link.amount
                        penalty_nab += nab_link.penalty_nab
                    if line.attendance_id.type=='kj':
                        line.write({
                                'work_day': 1.0,
                                # 'unit_price': price, 
                                'premi': line.min_wage_value < wage_value and wage_value - line.min_wage_value or 0.0,
                                'penalty': line.min_wage_value > wage_value and  line.min_wage_value - wage_value or 0.0,
                                'penalty_nab': penalty_nab,
                            })
                    else:
                        # JIKA NA, semua HITUNGAN UPAH HASIL dimasukkan ke PREMI 
                        line.write({
                                'work_day': 0.0,
                                # 'unit_price': price, 
                                'premi': wage_value - penalty_nab,
                                'penalty': 0.0,
                            })
                else:
                    line.write({
                            'work_day': 0.0,
                            # 'unit_price': price, 
                            'premi': 0.0,
                            'penalty': 0.0,
                            'penalty_nab': 0.0,
                        })
            lhm.write({'nab_allocated': True})

    @api.multi
    def run_progress_target(self):
        lhm_progress_list   = []
        lhm_removed_list    = []
        sequence_number     = 1
        progress_line_obj   = self.env['lhm.transaction.process.line']
        # if self.mapped('process_line_ids').filtered(lambda x: x.activity_id.is_panen):
        #     for data in self.mapped('process_line_ids').filtered(lambda x: x.activity_id.is_panen):
        #         lhm_progress_list.append(data.id)
        for data in self.mapped('process_line_ids'):
            lhm_progress_list.append(data.id)
        self.env.cr.execute("""
            select ltl.activity_id,
                ltl.location_id,
                sum(ltl.work_day) as hk,
                sum(ltl.work_day*ltl.min_wage_value)+sum(coalesce(ltl.premi,0.0)+coalesce(ltl.overtime_value,0.0)-coalesce(ltl.penalty,0.0)) as realisasi,
                sum(ltl.work_result) as nilai,
                sum(coalesce(ltl.premi,0.0)+coalesce(ltl.overtime_value,0.0)-coalesce(ltl.penalty,0.0)) as premi,
                sum(ltl.non_work_day) as hkne,
                sum(ltl.min_wage_value_date)+sum(ltl.work_day*ltl.min_wage_value)+sum(coalesce(ltl.premi,0.0)+coalesce(ltl.overtime_value,0.0)-coalesce(ltl.penalty,0.0))-sum(CASE WHEN ltl.min_wage_value_date > 0 THEN ltl.min_wage_value ELSE 0 END) as realisasi_date
            from lhm_transaction_line ltl
                left join lhm_activity la on ltl.activity_id = la.id
            where ltl.activity_id is not NULL and lhm_id = %s 
            group by ltl.activity_id, ltl.location_id;
            """, (self.id,))
        for progres in self.env.cr.dictfetchall():
            activity_data = self.env['lhm.activity'].search([('id', '=', progres['activity_id'])])
            if lhm_progress_list:
                progress_line   = progress_line_obj.search([('activity_id', '=', progres['activity_id']), ('location_id', '=', progres['location_id']), ('lhm_id', '=', self.id)])
                if progress_line and len(progress_line) > 1:
                    raise ValidationError(_("Terjadi kesalahan (T.T), Error Code %s. \n"
                                            "Hubungi administrator untuk informasi lebih lanjut!"))
                elif progress_line:
                    # if progress_line.nilai != progres['nilai'] and progress_line.activity_id.is_panen:
                    if progress_line.nilai != progres['nilai']:
                        progress_line.write({'nilai' : progres['nilai'], 'updated': True,})
                    if progress_line.work_day != progres['hk']:
                        progress_line.write({'work_day'  : progres['hk'], 'updated': True,})
                    if progress_line.non_work_day != progres['hkne']:
                        progress_line.write({'non_work_day'  : progres['hkne']})
                    if progress_line.realization != progres['realisasi']:
                        progress_line.write({'realization'   : progres['realisasi'], 'updated': True,})
                    if progress_line.realization_date != progres['realisasi_date']:
                        progress_line.write({'realization_date'   : progres['realisasi_date']})
                    if progress_line.premi != progres['premi']:
                        progress_line.write({'premi' : progres['premi'], 'updated': True,})
                    lhm_removed_list.append(progress_line.id)
                else:
                    new_lines = {
                        'sequence'          : sequence_number,
                        'date'              : self.date,
                        'activity_id'       : progres['activity_id'],
                        'location_id'       : progres['location_id'],
                        'nilai'             : progres['nilai'],
                        'uom_id'            : activity_data and activity_data.uom_id.id or False,
                        'nilai2'            : 0,
                        'uom2_id'           : activity_data and activity_data.uom2_id.id or False,
                        'work_day'          : progres['hk'],
                        'non_work_day'      : progres['hkne'],
                        'realization'       : progres['realisasi'],
                        'realization_date'  : progres['realisasi_date'],
                        'premi'             : progres['premi'],
                        'lhm_id'            : self.id,
                    }
                    if new_lines:
                        progress_line_obj.create(new_lines)
                        sequence_number     += 1
            else:
                new_lines = {
                    'sequence'          : sequence_number,
                    'date'              : self.date,
                    'activity_id'       : progres[0],
                    'location_id'       : progres[1],
                    'nilai'             : progres[4],
                    'uom_id'            : activity_data and activity_data.uom_id.id or False,
                    'nilai2'            : 0,
                    'uom2_id'           : activity_data and activity_data.uom2_id.id or False,
                    'work_day'          : progres[2],
                    'non_work_day'      : progres[6],
                    'realization'       : progres[3],
                    'realization_date'  : progres[7],
                    'premi'             : progres[5],
                    'lhm_id'            : self.id,
                }
                if new_lines:
                    progress_line_obj.create(new_lines)
                    sequence_number += 1

        employee_ids    = []
        for line in self.lhm_line_ids:
            if line.attendance_id and line.employee_id and \
                    line.employee_id.type_id and line.employee_id.type_id.monthly_employee and line.employee_id.id not in employee_ids \
                    and line.valid and (line.work_day > 0 or line.non_work_day > 0):
                employee_ids.append(line.employee_id.id)
        if employee_ids:
            self.check_all(self.account_period_id.date_start, self.account_period_id.date_stop, employee_ids)

    @api.multi
    def work_day_validation(self):
        self.ensure_one()
        LHMLine = self.env['lhm.transaction.line']
        # Panen First Priority
        # for line in sorted(self.lhm_line_ids.filtered(lambda x: x.activity_id and x.activity_id.is_panen), \
                        # key=lambda x: x.id):
        attend_na = self.env['hr.attendance.type'].search([('type','=','na')]) 
        attend_kj = self.env['hr.attendance.type'].search([('type','=','kj')]) 
        for line in self.lhm_line_ids:
            if line.lhm_input_type!='work_target':
                continue
            if not line.attendance_id:
                continue
            # Panen activity
            if line.activity_id.is_panen:
                # Check perhaps he is doing other activity panen
                other_lines = LHMLine.search([('employee_id','=',line.employee_id.id), 
                    ('attendance_id.type','=','kj'), 
                    ('lhm_id.date','=',line.lhm_id.date), 
                    ('lhm_id.lhm_input_type','=','work_target'), 
                    ('activity_id.is_panen','=',True), 
                    ('id','<',line.id), 
                    ])
                if other_lines and line.attendance_id.type=='kj':
                    line.attendance_id = attend_na and attend_na[0].id or line.attendance_id.id
            # non Panen activity
            if not line.activity_id.is_panen:
                # Check perhaps he is doing activity panen
                panen_lines = LHMLine.search([('employee_id','=',line.employee_id.id), 
                    ('attendance_id','!=',False), 
                    ('lhm_id.date','=',line.lhm_id.date), 
                    ('lhm_id.lhm_input_type','=','work_target'), 
                    ('work_result','>',0), 
                    ('activity_id.is_panen','=',True), 
                    ('id','!=',line.id), 
                    ])
                default_work_day = panen_lines and 1.0 or 0.0
                # And then we check other activity of the same employee
                other_lines = LHMLine.search([('employee_id','=',line.employee_id.id), 
                    ('attendance_id','!=',False), 
                    ('attendance_id.type','=','kj'), 
                    ('lhm_id.date','=',line.lhm_id.date), 
                    ('lhm_id.lhm_input_type','=','work_target'), 
                    ('work_result','>',0), 
                    ('activity_id.is_panen','=',False), 
                    ('id','<',line.id), 
                    ])
                for oth in other_lines:
                    if default_work_day < 1.0:
                        default_work_day += oth.work_day
                if default_work_day < 1.0:
                    if (default_work_day + line.work_day) < 1.0:
                        value = line.unit_price*line.work_result
                        line.work_day = line.work_day
                        line.premi = 0.0
                    elif (default_work_day + line.work_day) == 1.0:
                        value = line.unit_price*line.work_result
                        premi_amt = 0.0
                        if value > line.min_wage_value:
                            premi_amt = value - line.min_wage_value
                        line.premi = premi_amt
                    else:
                        value = line.unit_price*line.work_result
                        diff_work_day = 1.0 - default_work_day
                        line.work_day = diff_work_day
                        line.premi = value - (diff_work_day * line.min_wage_value)
                else:
                    value = line.unit_price*line.work_result
                    line.work_day = 0.0
                    line.attendance_id = attend_na and attend_na[0].id or line.attendance_id.id
                    line.premi = value

    @api.multi
    def compute_line_value(self):
        self.ensure_one()
        LHMLine = self.env['lhm.transaction.line']
        # Panen First Priority
        # for line in sorted(self.lhm_line_ids.filtered(lambda x: x.activity_id and x.activity_id.is_panen), \
                        # key=lambda x: x.id):
        attend_na = self.env['hr.attendance.type'].search([('type','=','na')]) 
        attend_kj = self.env['hr.attendance.type'].search([('type','=','kj')]) 
        for line in self.lhm_line_ids:
            if not line.attendance_id:
                continue
            if line.dummy_skip:
                continue
            
            # 1. Alokasi Min Wage. Antisipasi jika gagal onchange
            MinWage = self.env['hr.minimum.wage']
            base_min_wage = min_wage = False
            if line.employee_id and line.employee_id.basic_salary_type == 'employee':
                base_min_wage = MinWage.search([('employee_id', '=', line.employee_id.id), 
                        ('activity_id','=',False), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)
                # 2. Cari UMR yg ber Aktifitas
                min_wage = MinWage.search([('employee_id', '=', line.employee_id.id), 
                    ('activity_id','=',line.activity_id.id), ('date_from', '<=', self.date), 
                    ('date_to', '>=', self.date)], limit=1)
            elif line.employee_id and line.employee_id.basic_salary_type == 'employee_type':
                base_min_wage = MinWage.search([('employee_type_id', '=', line.employee_id.type_id.id), 
                        ('activity_id','=',False), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)
                min_wage = MinWage.search([('employee_type_id', '=', line.employee_id.type_id.id),
                    ('activity_id','=',line.activity_id.id), ('date_from', '<=', self.date), 
                    ('date_to', '>=', self.date)], limit=1)
            min_wage = min_wage and min_wage[0] or (base_min_wage and base_min_wage[0] or False)
            if not min_wage:
                raise ValidationError(_('Tidak dapat menemukan UMR atas Karyawan [%s] %s di LHM %s')%(line.employee_id.no_induk, line.employee_id.name, self.name))
            # 1.1. Set UMR
            min_wage_value = min_wage and (min_wage.umr_month / (min_wage.work_day or 25)) or 0.0
            line.min_wage_id = min_wage.id
            line.min_wage_value = min_wage_value
            # 2. Hitung Lembur
            if line.overtime_hour and line.overtime_hour > 0:
                holiday         = False
                overtime_data   = self.env['hr.overtime'].search([('hours', '=', line.overtime_hour)], limit=1)
                holiday_data    = self.env['hr.holidays.public.line'].search([('date', '=', line.date)])
                if holiday_data:
                    holiday     = True
                if overtime_data and line.employee_id.type_id and line.employee_id.type_id.overtime_calc:
                    if holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                        line.overtime_value = (line.min_wage_id.umr_month / 173) * overtime_data.holiday
                    elif not holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                        line.overtime_value = (line.min_wage_id.umr_month / 173) * overtime_data.normal_day
                    else:
                        line.overtime_value = 0
                if overtime_data and line.employee_id.type_id and not line.employee_id.type_id.overtime_calc:
                    if holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                        line.overtime_value = (line.min_wage_id.umr_month / 25) * float(float(3) / float(20)) * overtime_data.holiday
                    elif not holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                        line.overtime_value = (line.min_wage_id.umr_month / 25) * float(float(3) / float(20)) * overtime_data.normal_day
                    else:
                        line.overtime_value = 0
            # 3. Compute Value Salary untuk LHM Target
            if line.lhm_input_type!='work_target':
                continue
            # Rawat / non Panen activity
            if not line.activity_id.is_panen:
                price = min_wage.get_rate_rawat(self.env['lhm.plant.block'].search([('location_id','=',line.location_id.id)], limit=1)[-1].year, uom_id=line.satuan_id.id)
                line.unit_price = price
                value = price*line.work_result
                if line.attendance_id.type=='kj':
                    line.work_day = (value/min_wage_value) if (value < min_wage_value) else 1
                    line.premi = (value - min_wage_value) if (value > min_wage_value) else 0.0
                elif line.attendance_id.type=='na':
                    line.work_day = 0.0
                    line.premi = value

    @api.multi
    def run_progress(self):
        super(lhm_transaction, self).run_progress()
        # Hitung ulang tonase di Progress nya
        # self.filtered(lambda x: x.nab_allocated).update_salary_based_on_target()
        for lhm in self.filtered(lambda x: x.lhm_input_type=='work_target'):
            lhm.compute_line_value()
            lhm.work_day_validation()
            lhm.run_progress_target()

class lhm_transaction_line_nab_line(models.Model):
    _inherit = 'lhm.transaction.line.nab.line'

    unit_price = fields.Float('Price Unit')
    amount = fields.Float('Amount')
    penalty_nab = fields.Float('Penalty NAB')
    contractor_line_id = fields.Many2one('lhm.contractor.line', 'Buku Kontraktor Line', ondelete='cascade')
    contractor_id = fields.Many2one('lhm.contractor', related='contractor_line_id.contractor_id', string='Buku Kontraktor')
    supplier_id = fields.Many2one('res.partner', related='contractor_id.supplier_id', string='Kontraktor')
    contractor_date = fields.Date(related='contractor_line_id.date', string='Kontraktor')
    date = fields.Date(compute='_compute_realisation_date', string='Periode Penggajian', store=True)

    @api.multi
    @api.depends('nab_line_id', 'nab_line_id.lhm_nab_id.date_pks', 'nab_line_id.force_date')
    def _compute_realisation_date(self):
        for link in self:
            if link.nab_line_id and link.nab_line_id.lhm_nab_id and link.nab_line_id.lhm_nab_id.date_pks: 
                link.date = link.nab_line_id.force_date and link.nab_line_id.force_date or link.nab_line_id.lhm_nab_id.date_pks
            else:
                link.date = False

    @api.multi
    @api.constrains('lhm_line_id', 'nab_line_id', 'contractor_line_id')
    def _check_double_link(self):
        check = True
        for line in self:
            if line.lhm_line_id:
                other_line = self.search([('id','!=',line.id),('lhm_line_id','=',line.lhm_line_id.id),('nab_line_id','=',line.nab_line_id.id)])
                if other_line:
                    raise ValidationError(_('Alokasi antara Detail NAB dan Detail LHM hanya bisa 1 kali!'))
            if line.contractor_line_id:
                other_line = self.search([('id','!=',line.id),('contractor_line_id','=',line.contractor_line_id.id),('nab_line_id','=',line.nab_line_id.id)])
                if other_line:
                    raise ValidationError(_('Alokasi antara Detail NAB dan Detail Buku Kontraktor hanya bisa 1 kali!'))

class lhm_transaction_line(models.Model):
    _inherit = 'lhm.transaction.line'
    
    lhm_input_type = fields.Selection([('reguler','Reguler'),('work_target','Target Pekerjaan')], string='Transaction Type', compute='_get_lhm_input_type', store=True)
    premi_other = fields.Float('Premi Nab')
    penalty_nab = fields.Float('Penalty Nab')
    penalty_other = fields.Float('Penalty Other')
    dummy_skip  = fields.Boolean('Dummy Skip Update')
    pending_work_result = fields.Float(compute='_get_panen_target_status', string='Outstanding', store=True)
    target_state = fields.Selection([('draft','New'),('unallocated','Unallocated'),('outstanding','Still Pending'),('done','Done')], 
        compute='_get_panen_target_status', string='Status Panen', store=True)

    @api.multi
    @api.depends('lhm_id.lhm_input_type')
    def _get_lhm_input_type(self):
        for line in self:
            line.lhm_input_type = line.lhm_id.lhm_input_type

    @api.multi
    @api.depends('lhm_id.state', 'lhm_id.lhm_input_type', 'activity_id', 'dummy_skip', 
        'lhm_nab_ids', 'lhm_nab_ids.nab_id.state', 'lhm_nab_ids.nilai')
    def _get_panen_target_status(self):
        for line in self:
            if not line.activity_id.is_panen:
                line.target_state = False
                line.pending_work_result = 0.0
                continue
            if line.lhm_input_type!='work_target':
                if line.lhm_id.state not in ('draft', 'cancel'):
                    line.target_state = 'done'
                    line.pending_work_result = 0.0
                else:
                    line.target_state = 'draft'
                continue
            pending_work_result = line.work_result
            if line.dummy_skip:
                line.pending_work_result = 0.0
                line.target_state = 'done'
                continue
            if line.lhm_id.state=='draft':
                state = 'draft'
            elif line.lhm_id.state not in ('draft', 'cancel'):
                state='unallocated'
            
            for link in line.lhm_nab_ids:
                pending_work_result-=link.nilai
            if pending_work_result and pending_work_result>0.0 and pending_work_result<line.work_result:
                state='outstanding'
            elif pending_work_result==0.0:
                state='done'
            
            line.pending_work_result = pending_work_result
            line.target_state = state

    @api.multi
    def _check_work_day(self):
        for line in self:
            if line.attendance_id and line.attendance_id.special and line.attendance_id.type == 'kj':
                if line.work_day <= 0 and line.lhm_id.lhm_input_type!='work_target':
                    raise UserError(_('HK Wajib Diisi!'))

    @api.onchange('lhm_input_type', 'employee_id', 'attendance_id', 'activity_id', 'location_id', 'work_result', 'satuan_id')
    def _onchange_value(self):
        if self.lhm_input_type=='work_target':
            MinWage = self.env['hr.minimum.wage']
            base_min_wage = False
            if self.employee_id and self.employee_id.basic_salary_type == 'employee':
                base_min_wage = MinWage.search([('employee_id', '=', self.employee_id.id), 
                        ('activity_id','=',False), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)
            elif self.employee_id and self.employee_id.basic_salary_type == 'employee_type':
                base_min_wage = MinWage.search([('employee_type_id', '=', self.employee_id.type_id.id), 
                        ('activity_id','=',False), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)
            # SET HR MINIMUM WAGE KHUSUS UNTUK NON PANEN / RAWAT
            if self.employee_id and self.activity_id and not self.activity_id.is_panen and self.location_id \
                    and self.location_id.type_id.oil_palm and self.satuan_id:
                # Ganti Minimim Wage
                # min_wage    = self.min_wage_id
                if self.employee_id and self.employee_id.basic_salary_type == 'employee':
                    min_wage = MinWage.search([('employee_id', '=', self.employee_id.id), 
                        ('activity_id','=',self.activity_id.id), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)
                elif self.employee_id and self.employee_id.basic_salary_type == 'employee_type':
                    min_wage = MinWage.search([('employee_type_id', '=', self.employee_id.type_id.id),
                        ('activity_id','=',self.activity_id.id), ('date_from', '<=', self.date), 
                        ('date_to', '>=', self.date)], limit=1)    
                min_wage = min_wage and min_wage[-1] or base_min_wage
                min_wage_value = min_wage and (min_wage.umr_month / (min_wage.work_day or 25)) or 0.0
                self.min_wage_id = min_wage.id
                self.min_wage_value = min_wage_value
                price = min_wage.get_rate_rawat(self.env['lhm.plant.block'].search([('location_id','=',self.location_id.id)], limit=1)[-1].year, uom_id=self.satuan_id.id)
                self.unit_price = price
                value = price*self.work_result
                if self.attendance_id.type=='kj':
                    self.work_day = value>min_wage_value and 1.0 or (min_wage_value and value/min_wage_value or 0.0)
                    self.premi = value>min_wage_value and value-min_wage_value or 0.0
                elif self.attendance_id.type=='na':
                    self.work_day = 0.0
                    self.premi = value
            else:
                self.min_wage_id = base_min_wage.id
                self.min_wage_value = base_min_wage and (base_min_wage.umr_month / (base_min_wage.work_day or 25)) or 0.0
                self.work_day = 0.0
                self.premi = 0.0
                self.unit_price = 0.0

class lhm_contractor_line(models.Model):
    _inherit = 'lhm.contractor.line'

    nab_line_ids = fields.One2many('lhm.transaction.line.nab.line', 'contractor_line_id', 'NAB Detail')
    nab_allocated = fields.Boolean('NAB Allocated')
    compute_from = fields.Selection([('nilai','Hasil 1'), ('nilai2','Hasil 2')], 'Subtotal Dari', default='nilai')
    premi = fields.Float('Premi')
    penalty = fields.Float('Penalty')
    penalty_nab = fields.Float('Penalty Nab')
    total = fields.Float('Nilai', compute='_compute_harga_satuan', store=True, readonly=True)
    panen = fields.Boolean('Panen', related='activity_id.is_panen', store=True, readonly=True)

    @api.depends('unit_price', 'nilai', 'nilai2', 'compute_from', 'premi', 'penalty', 'penalty_nab')
    def _compute_harga_satuan(self):
        for line in self:
            if line.compute_from=='nilai':
                line.total = (line.unit_price * line.nilai) + (line.premi - line.penalty - line.penalty_nab)
            else:
                line.total = (line.unit_price * line.nilai2) + (line.premi - line.penalty - line.penalty_nab)

class lhm_nab(models.Model):
    _inherit = 'lhm.nab'

    force_date = fields.Date('Force Date', help="Tanggal diakuinya NAB kedalam Produksi Harian")
    pemanen_line_ids = fields.One2many('lhm.nab.pemanen.line', 'lhm_nab_id', string='Detail Pemanen', readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})

    @api.multi
    def button_draft(self):
        for nab in self:
            #VALIDASI
            for tgl_panen in nab.line_ids.mapped('tgl_panen'):
                daftar_upah = self.env['plantation.salary'].search([('from_date','<=',tgl_panen), \
                    ('to_date','>=',tgl_panen),('state','!=','draft'), \
                    ('lhm_input_type','=','work_target')], limit=1)
                if daftar_upah:
                    raise ValidationError(_("Tidak dapat Set to Draft. \n \
                        NAB sudah teralokasikan di periode penggajian %s s/d %s. \n \
                        Silahkan di Cancel terlebih dahulu Daftar Upahnya.")% \
                        (daftar_upah.from_date, daftar_upah.to_date))
            for link in nab.line_ids.mapped('lhm_line_ids').filtered(lambda x:x.contractor_line_id):
                if link.contractor_id.state!='draft':
                    raise ValidationError(_("Tidak dapat Set to Draft. \n \
                        NAB sudah teralokasikan di Buku Kontraktor atas Kontraktor %s. \n \
                        Silahkan di Set to draft Buku Kontraktornya.")% \
                        link.contractor_id.name)

            nab.line_ids.mapped('lhm_progress_ids').mapped('lhm_id').write({'nab_allocated': False})
            lhm_to_update = self.env['lhm.transaction']
            for link_lhm in nab.line_ids.mapped('lhm_line_ids'):
                lhm_to_update |= link_lhm.lhm_id
                link_lhm.unlink()
            lhm_to_update.update_salary_based_on_target()
            for lhm in lhm_to_update:
                lhm.run_progress_target()
                for progress in lhm.process_line_ids:
                    progress.write({'nilai2': sum([x.compute_weight() for x in progress.nab_line_ids.filtered(lambda x: x.id not in nab.line_ids.ids)])})
        return super(lhm_nab, self).button_draft()

    @api.multi
    def button_confirm(self):
        for nab in self:
            #VALIDASI
            for tgl_panen in nab.line_ids.mapped('tgl_panen'):
                daftar_upah = self.env['plantation.salary'].search([('from_date','<=',tgl_panen), \
                    ('to_date','>=',tgl_panen),('state','!=','draft'), \
                    ('lhm_input_type','=','work_target')], limit=1)
                if daftar_upah:
                    raise ValidationError(_("Tidak dapat Confirm. \n \
                        Sudah terdapat Daftar Upah yg berstatus Confirm di periode penggajian %s s/d %s. \n \
                        Silahkan di Cancel terlebih dahulu Daftar Upahnya.")% \
                        (daftar_upah.from_date, daftar_upah.to_date))

        res = super(lhm_nab,self).button_confirm()
        self.mapped('line_ids').mapped('lhm_progress_ids').mapped('lhm_id').update_salary_based_on_target()
        for lhm in self.mapped('line_ids').mapped('lhm_progress_ids').mapped('lhm_id'):
            lhm.run_progress_target()

    @api.multi
    def button_revise(self):
        for nab in self:
            #VALIDASI
            for tgl_panen in nab.line_ids.mapped('tgl_panen'):
                daftar_upah = self.env['plantation.salary'].search([('from_date','<=',tgl_panen), \
                    ('to_date','>=',tgl_panen),('state','!=','draft'), \
                    ('lhm_input_type','=','work_target')], limit=1)
                if daftar_upah:
                    raise ValidationError(_("Tidak dapat Revisi. \n \
                        NAB sudah teralokasikan di periode penggajian %s s/d %s. \n \
                        Silahkan di Cancel terlebih dahulu Daftar Upahnya.")% \
                        (daftar_upah.from_date, daftar_upah.to_date))
            for link in nab.line_ids.mapped('lhm_line_ids').filtered(lambda x:x.contractor_line_id):
                if link.contractor_id.state!='draft':
                    raise ValidationError(_("Tidak dapat Revisi. \n \
                        NAB sudah teralokasikan di Buku Kontraktor atas Kontraktor %s. \n \
                        Silahkan di Set to draft Buku Kontraktornya.")% \
                        line.supplier_id.name)
            lhm_to_update = self.env['lhm.transaction']
            for link_lhm in nab.line_ids.mapped('lhm_line_ids'):
                lhm_to_update |= link_lhm.lhm_id
                link_lhm.unlink()
            lhm_to_update.update_salary_based_on_target()
            for lhm in lhm_to_update:
                lhm.run_progress_target()
                for progress in lhm.process_line_ids:
                    progress.write({'nilai2': sum([x.compute_weight() for x in progress.nab_line_ids.filtered(lambda x: x.id not in nab.line_ids.ids)])})
        return super(lhm_nab,self).button_revise()

    @api.multi
    def button_approve_revision(self):
        for nab in self:
            #VALIDASI
            for tgl_panen in nab.line_ids.mapped('tgl_panen'):
                daftar_upah = self.env['plantation.salary'].search([('from_date','<=',tgl_panen), \
                    ('to_date','>=',tgl_panen),('state','!=','draft'), \
                    ('lhm_input_type','=','work_target')], limit=1)
                if daftar_upah:
                    raise ValidationError(_("Tidak dapat Update Revisi. \n \
                        Sudah terdapat Daftar Upah yg berstatus Confirm di periode penggajian %s s/d %s. \n \
                        Silahkan di Cancel terlebih dahulu Daftar Upahnya.")% \
                        (daftar_upah.from_date, daftar_upah.to_date))

        res = super(lhm_nab,self).button_approve_revision()
        self.mapped('line_ids').mapped('lhm_progress_ids').mapped('lhm_id').update_salary_based_on_target()
        for lhm in self.mapped('line_ids').mapped('lhm_progress_ids').mapped('lhm_id'):
            lhm.run_progress_target()

class lhm_nab_line(models.Model):
    _inherit = "lhm.nab.line"
    
    force_date = fields.Date('Periode Penggajian', help="Tanggal diakuinya NAB kedalam Produksi Harian")
    dummy_skip  = fields.Boolean('Dummy Skip Update')
    pemanen_line_ids = fields.One2many('lhm.nab.pemanen.line', 'nab_line_id', 'Detail Pemanen')

    @api.onchange('block_id','tgl_panen')
    def onchange_block(self):
        self.ensure_one()
        pemanen_line_res = []
        contractor_lines = self.env['lhm.contractor.line'].search([('date','=',self.tgl_panen),
                ('location_id','=',self.block_id.location_id.id),
                ('contractor_id','!=',False),
                ('activity_id.is_panen','=',True),
                ])
        for line in contractor_lines:
            work_result_allocated = sum(line.mapped('nab_line_ids').mapped('nilai'))
            if line.nilai > work_result_allocated:
                pemanen_line_res.append({
                    'employee_id': False,
                    'partner_id': line.contractor_id.supplier_id.id,
                    'work_result_pending': line.nilai-work_result_allocated,
                    'work_result': line.nilai-work_result_allocated,
                    })
        lhm_lines = self.env['lhm.transaction.line'].search([('lhm_id.date','=',self.tgl_panen),
                ('location_id','=',self.block_id.location_id.id),
                ('lhm_id.state','!=','draft'),
                ('activity_id.is_panen','=',True),
                ])
        for lhmline in lhm_lines:
            work_result_allocated = sum(lhmline.mapped('lhm_nab_ids').mapped('nilai'))
            if lhmline.work_result > work_result_allocated:
                pemanen_line_res.append({
                    'partner_id': False,
                    'employee_id': lhmline.employee_id.id,
                    'work_result_pending': lhmline.work_result-work_result_allocated,
                    'work_result': lhmline.work_result-work_result_allocated,
                    })
        self.pemanen_line_ids = map(lambda x: (0,0,x), pemanen_line_res)

    @api.onchange('pemanen_line_ids')
    def onchange_pemanen(self):
        self.ensure_one()
        total_qty = 0.0
        for line in self.pemanen_line_ids:
            total_qty += line.work_result
        self.qty_nab = total_qty

    @api.onchange('force_date')
    def onchange_force_date(self):
        self.ensure_one()
        if self.force_date:
            if self.force_date < self.tgl_panen:
                self.force_date = False
                return {
                        'warning': {'title': _('Kesalahan Input Tanggal'),
                                    'message': _("Tanggal Periode Penggajian tidak diperbolehkan sebelum Tanggal Panen")},
                    }
            elif self.env['plantation.salary'].search([('from_date','<=',self.force_date), \
                    ('to_date','>=',self.force_date),('state','!=','draft'), \
                    ('lhm_input_type','=','work_target')]):
                force_date = datetime.strptime(self.force_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                self.force_date = False
                return {
                        'warning': {'title': _(('Periode Penggajian Tanggal %s Salah ')%force_date),
                                    'message': _("Periode Penggajian tersebut sudah terjadi")},
                    }

    @api.multi
    @api.depends('lhm_nab_id.state','lhm_line_ids','lhm_line_ids.lhm_id.state',
        'lhm_line_ids.lhm_line_id.location_id','lhm_line_ids.lhm_line_id.activity_id',
        'lhm_line_ids.lhm_line_id.work_result','lhm_line_ids.contractor_line_id.nilai',
        'lhm_line_ids.contractor_line_id.activity_id','lhm_line_ids.contractor_line_id.location_id')
    def _check_allocation_state(self):
        for line in self:
            # total_allocation = sum(line.lhm_line_ids.mapped('nilai'))
            contractor_lines = self.env['lhm.contractor.line'].search([('date','=',line.tgl_panen),
                                            ('location_id','=',line.block_id.location_id.id),
                                            ('activity_id.is_panen','=',True),
                                            ])
            c_total_janjang = sum(contractor_lines.mapped('nilai'))
            p_total_janjang = sum(line.mapped('lhm_progress_ids').mapped('nilai'))
            total_panen = c_total_janjang + p_total_janjang
            total_allocation = 0.0
            for xline in line.lhm_line_ids:
                if xline.contractor_line_id and xline.contractor_line_id.activity_id.is_panen \
                        and xline.contractor_line_id.location_id.id==line.block_id.location_id.id:
                    total_allocation+=xline.contractor_line_id.nilai
                if xline.lhm_line_id and xline.lhm_line_id.activity_id.is_panen \
                        and xline.lhm_line_id.location_id.id==line.block_id.location_id.id:
                    if total_panen:
                        total_allocation+=(xline.lhm_line_id.work_result/total_panen)*line.qty_nab
            if round(total_allocation,2) < line.qty_nab:
                line.pending_allocation = True
            else:
                line.pending_allocation = False
    
    pending_allocation  = fields.Boolean('Pending Allocaton', compute='_check_allocation_state', store=True)
    
    @api.multi
    def allocate_nab_line_to_lhm_line(self):
        lhm_to_update = self.env['lhm.transaction']
        for nab_line in self.filtered(lambda x: x.pending_allocation):
            if nab_line.dummy_skip:
                continue
            # Decrese Total Tonase from Buku Kontraktor
            for x in nab_line.lhm_line_ids:
                if x.contractor_line_id:
                    x.contractor_line_id.write({'nilai2': x.contractor_line_id.nilai2 - x.nilai2})
            # After update lhm contractor line, we delete all link
            nab_line.lhm_line_ids.unlink()

            vals = []
            # Dengan Alokasi Pemanen Manual
            if nab_line.pemanen_line_ids:
                # 1. Cek Total Qty Pemanen x QTY NAB
                if nab_line.qty_nab != sum(nab_line.pemanen_line_ids.mapped('work_result')):
                    raise ValidationError(_("Block %s Tanggal Panen %s Salah.\n\
                        Qty Panen di NAB (%s) tidak sesuai dengan Total \
                        Qty Panen (%s) dari Pemanen yg dicantumkan")% \
                        (str(nab_line.block_id.code), nab_line.tgl_panen, str(nab_line.qty_nab), \
                            str(sum(nab_line.pemanen_line_ids.mapped('work_result')))))
                # 2. Alokasikan
                update_progress = {}
                for line in nab_line.pemanen_line_ids:
                    # Jika Panen dari Kontraktor, maka Panen tersebut dari Buku Kontraktor
                    work_result = line.work_result
                    if line.partner_id:
                        contractor_lines = self.env['lhm.contractor.line'].search([('date','=',nab_line.tgl_panen),
                                ('location_id','=',nab_line.block_id.location_id.id),
                                ('contractor_id.supplier_id','=',line.partner_id.id),
                                ('activity_id.is_panen','=',True), ('contractor_id.state','=','draft')
                                ])
                        if not contractor_lines:
                            raise ValidationError(_("Block %s Tanggal Panen %s Salah.\n\
                                Kontraktor %s tidak dapat ditemukan di Buku Kontraktor")% \
                                (str(nab_line.block_id.code), nab_line.tgl_panen, line.partner_id.name))
                        if line.work_result > sum(contractor_lines.mapped('nilai')):
                            raise ValidationError(_("Block %s Tanggal Panen %s Salah.\n\
                                Qty Panen Kontraktor %s (%s) tidak sesuai dengan Total \
                                Qty Panen (%s) di Buku Kontraktor")% \
                                (str(nab_line.block_id.code), nab_line.tgl_panen, line.partner_id.name,
                                    str(line.work_result), str(sum(contractor_lines.mapped('nilai')))))
                        for contractor_line in contractor_lines:
                            if not work_result:
                                continue
                            other_nab_janjang = sum(contractor_line.mapped('nab_line_ids').mapped('nilai'))
                            other_nab_tonase = sum(contractor_line.mapped('nab_line_ids').mapped('nilai2'))
                            
                            if work_result > (contractor_line.nilai - other_nab_janjang):
                                work_result -= (contractor_line.nilai - other_nab_janjang)
                                nilai = (contractor_line.nilai - other_nab_janjang)
                            else:
                                nilai = work_result
                                work_result = 0.0
                                
                            vals.append((0,0,{
                                    'contractor_line_id': contractor_line.id,
                                    'nab_line_id': nab_line.id,
                                    'nilai': nilai,
                                    'uom_id': contractor_line.uom_id and contractor_line.uom_id.id or False,
                                    'nilai2': nab_line.qty_nab and (nilai/nab_line.qty_nab)*nab_line.compute_weight() or 0.0,
                                    'unit_price': contractor_line.unit_price,
                                    'amount': nab_line.qty_nab and contractor_line.unit_price*((nilai/nab_line.qty_nab)*nab_line.compute_weight()) or 0.0,
                                    'penalty_nab': (nilai/line.work_result)*line.amount_afkir,
                                }))
                            contractor_line.write({
                                    'nab_allocated': True,
                                    'nilai2': nab_line.qty_nab and other_nab_tonase + ((nilai/nab_line.qty_nab)*nab_line.compute_weight()) or 0.0,
                                    'penalty_nab': (nilai/line.work_result)*line.amount_afkir,
                                })
                        if work_result:
                            raise ValidationError(_("Tidak dapat menemukan asal Panen atas Kontraktor %s di Lokasi %s.\n\
                                Silahkan isi asal hasil Panen ini apakah dari Karyawan atau Pemanen Kontraktor")%
                                (line.partner_id, nab_line.block_id.code))
                    # Jika Panen dari Karyawan, maka Panen tersebut dari Laporan Harian Mandor
                    elif line.employee_id:
                        # Check if LHM is not there
                        check = False
                        for progress in nab_line.lhm_progress_ids:
                            lhm_lines = progress.lhm_id.mapped('lhm_line_ids').filtered(lambda x: x.location_id==progress.location_id \
                                    and x.activity_id==progress.activity_id and x.activity_id.is_panen \
                                    and x.employee_id.id==line.employee_id.id)
                            if lhm_lines:
                                check = True
                        if not check:
                            raise ValidationError(_("Block %s Tanggal Panen %s Salah.\n\
                                LHM dengan Karyawan (%s) %s tidak dapat ditemukan. \
                                Silahkan diperiksa terlebih dahulu. Pastikan LHMnya telah di Proses.")% \
                                (str(nab_line.block_id.code), nab_line.tgl_panen, line.employee_id.no_induk,
                                    line.employee_id.name))
                        for progress in nab_line.lhm_progress_ids:
                            if progress not in update_progress.keys():
                                update_progress.update({progress: {'nilai2':0.0}})
                            lhm_to_update |= progress.lhm_id
                            lhm_lines = progress.lhm_id.mapped('lhm_line_ids').filtered(lambda x: x.location_id==progress.location_id \
                                    and x.activity_id==progress.activity_id and x.activity_id.is_panen \
                                    and x.employee_id.id==line.employee_id.id)
                            for lhm_line in lhm_lines:
                                if not work_result:
                                    continue
                                other_nab_janjang = sum(lhm_line.mapped('lhm_nab_ids').mapped('nilai'))
                                other_nab_tonase = sum(lhm_line.mapped('lhm_nab_ids').mapped('nilai2'))
                                if not (lhm_line.work_result - other_nab_janjang):
                                    continue

                                if work_result > (lhm_line.work_result - other_nab_janjang):
                                    janjang = lhm_line.work_result - other_nab_janjang
                                    work_result -= lhm_line.work_result - other_nab_janjang
                                else:
                                    janjang = work_result
                                    work_result = 0.0
                                
                                berat = nab_line.qty_nab and (janjang/nab_line.qty_nab)*nab_line.compute_weight() or 0.0
                                if lhm_line.lhm_input_type=='work_target':
                                    price = lhm_line.min_wage_id.get_rate_panen(nab_line.block_id.year)
                                else:
                                    price = 0.0
                                vals.append((0,0,{
                                    'lhm_line_id': lhm_line.id,
                                    'nab_line_id': nab_line.id,
                                    'nilai': janjang,
                                    'uom_id': lhm_line.satuan_id and lhm_line.satuan_id.id or False,
                                    'nilai2': berat,
                                    'unit_price': price,
                                    'amount': price*berat,
                                    'penalty_nab': (janjang/line.work_result)*line.amount_afkir,
                                }))
                                update_progress[progress]['nilai2'] += berat
                                    # self.env['lhm.transaction.line.nab.line'].create(vals)
                        if work_result:
                            raise ValidationError(_("Tidak dapat menemukan asal Panen atas Karyawan (%s) %s di Lokasi %s.\n\
                                Silahkan isi asal hasil Panen ini apakah dari Karyawan atau Pemanen Kontraktor")%
                                (line.employee_id.no_induk, line.employee_id.name, nab_line.block_id.code))
                    else:
                        raise ValidationError(_("Tidak memiliki asal Panen.\nSilahkan \
                            isi asal hasil Panen ini apakah dari Karyawan atau Pemanen Kontraktor"))
                for progress, value in update_progress.items():
                    progress.write(value)
            # Tanpa Alokasi Pemanen Manual, maka System akan mengalokasikan otomatis
            else:
                # Jika Ada Panen Vendor Borongan
                contractor_lines = self.env['lhm.contractor.line'].search([('date','=',nab_line.tgl_panen),
                                                ('location_id','=',nab_line.block_id.location_id.id),
                                                ('activity_id.is_panen','=',True), ('contractor_id.state','=','draft')
                                                ])
                c_total_janjang = sum(contractor_lines.mapped('nilai'))
                p_total_janjang = sum(nab_line.mapped('lhm_progress_ids').mapped('nilai'))
                total_panen = c_total_janjang + p_total_janjang
                if not nab_line.mapped('lhm_progress_ids') and not contractor_lines:
                    raise ValidationError(_("Tidak dapat menemukan LHM.\nSilahkan \
                            input LHM dan Progress LHMnya sebelum membuat NAB"))
                if total_panen < nab_line.qty_nab:
                    raise ValidationError(_("Total Progress Panen dari LHM untuk Blok %s lebih \n \
                            sedikit dibandingkan dengan NAB yg dikeluarkan"))
                    # continue
                for contractor_line in contractor_lines:
                    prev_total = sum(contractor_line.mapped('nab_line_ids').mapped('nilai2'))
                    vals.append((0,0,{
                            'contractor_line_id': contractor_line.id,
                            'nab_line_id': nab_line.id,
                            # 'nilai': contractor_line.nilai,
                            'nilai': total_panen and (contractor_line.nilai/total_panen)*nab_line.qty_nab or 0.0,
                            'uom_id': contractor_line.uom_id and contractor_line.uom_id.id or False,
                            'nilai2': total_panen and (contractor_line.nilai/total_panen)*nab_line.compute_weight() or 0.0,
                            'unit_price': contractor_line.unit_price,
                            'amount': total_panen and contractor_line.unit_price*((contractor_line.nilai/total_panen)*nab_line.compute_weight()) or 0.0,
                        }))
                    contractor_line.write({
                            'nab_allocated': True,
                            'nilai2': total_panen and prev_total + ((contractor_line.nilai/total_panen)*nab_line.compute_weight()) or 0.0,
                        })
                # Jika Ada Panen dari LHM
                for progress in nab_line.lhm_progress_ids:
                    lhm_to_update |= progress.lhm_id
                    lhm_lines = progress.lhm_id.mapped('lhm_line_ids').filtered(lambda x: x.location_id==progress.location_id and x.activity_id==progress.activity_id and x.activity_id.is_panen)
                    total_berat = 0.0
                    for line in lhm_lines:
                        janjang = total_panen and (line.work_result/total_panen)*nab_line.qty_nab or 0.0
                        berat = total_panen and (line.work_result/total_panen)*nab_line.compute_weight() or 0.0
                        total_berat += berat
                        if line.lhm_input_type=='work_target':
                            price = line.min_wage_id.get_rate_panen(nab_line.block_id.year)
                        else:
                            price = 0.0
                        vals.append((0,0,{
                            'lhm_line_id': line.id,
                            'nab_line_id': nab_line.id,
                            'nilai': janjang,
                            'uom_id': line.satuan_id and line.satuan_id.id or False,
                            'nilai2': berat,
                            'unit_price': price,
                            'amount': price*berat,
                        }))
                        # self.env['lhm.transaction.line.nab.line'].create(vals)
                    progress.write({'nilai2': total_berat})
            if vals:
                nab_line.write({'lhm_line_ids': vals})

        if lhm_to_update:
            lhm_to_update.update_salary_based_on_target()
            for lhm in lhm_to_update:
                lhm.run_progress_target()

class lhm_nab_pemanen_line(models.Model):
    _name = 'lhm.nab.pemanen.line'

    nab_line_id = fields.Many2one('lhm.nab.line', 'Nab Line Ref', ondelete="cascade")
    block_id = fields.Many2one('lhm.plant.block', related='nab_line_id.block_id', string='Blok')
    tgl_panen = fields.Date(related='nab_line_id.tgl_panen', string='Tgl. Panen')
    employee_id = fields.Many2one('hr.employee','Karyawan')
    no_induk = fields.Char(related='employee_id.no_induk',string='NIK')
    partner_id = fields.Many2one('res.partner','Kontraktor', domain="[('supplier','=',True)]")
    work_result = fields.Float('Qty Panen (Janjang)', required=True)
    work_result_pending = fields.Float('Work Result Pending)', readonly=True)
    afkir_qty = fields.Float('Qty Afkir')
    amount_afkir = fields.Float('Nilai Penalty Afkir')
    lhm_nab_id = fields.Many2one('lhm.nab', related='nab_line_id.lhm_nab_id', string='Nab Ref')

    @api.onchange('work_result')
    def onchange_work_result(self):
        self.ensure_one()
        if self.work_result > self.work_result_pending:
            self.work_result = self.work_result_pending
            return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Hasil Panen tidak dapat melebihi Pending Panen yg belum teralokasi")},
                }