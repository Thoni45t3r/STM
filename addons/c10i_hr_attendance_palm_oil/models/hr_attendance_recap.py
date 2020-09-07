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
import os
import tempfile

class hr_attendance_recap(models.Model):
    _name           = 'hr.attendance.recap'
    _inherit        = ['mail.thread']
    _description    = 'Attendance Recap'

    name                    = fields.Char("Name", default="/", track_visibility='onchange')
    book                    = fields.Binary(string='File Excel', track_visibility='onchange')
    book_filename           = fields.Char(string='File Name', track_visibility='onchange')
    date_from               = fields.Date('Date From', default=fields.Date.context_today, track_visibility='onchange')
    date_to                 = fields.Date('Date To', default=fields.Date.context_today, track_visibility='onchange')
    line_ids                = fields.One2many('hr.attendance.recap.line', 'recap_id', string="Details", )
    to_invoice_ids          = fields.One2many('hr.attendance.recap.to.invoice.line', 'recap_id', string="To Invoices")
    partner_id              = fields.Many2one('res.partner', string="Payroll", ondelete="restrict", default=lambda self: self.env['res.company']._company_default_get().attendance_partner_id)
    partner_kesehatan       = fields.Many2one('res.partner', string="BPJS Kesehatan", ondelete="restrict", default=lambda self: self.env['res.company']._company_default_get().attendance_partner_kesehatan)
    partner_ketenagakerjaan = fields.Many2one('res.partner', string="BPJS Ketenagakerjaan", ondelete="restrict", default=lambda self: self.env['res.company']._company_default_get().attendance_partner_ketenagakerjaan)
    partner_pensiun         = fields.Many2one('res.partner', string="BPJS Pensiun", ondelete="restrict", default=lambda self: self.env['res.company']._company_default_get().attendance_partner_pensiun)
    partner_keselamatan     = fields.Many2one('res.partner', string="JKK + JKM", ondelete="restrict", default=lambda self: self.env['res.company']._company_default_get().attendance_partner_keselamatan)
    date_invoice            = fields.Date("Invoice Date")
    company_id              = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    error_note              = fields.Text("Error Note")
    note                    = fields.Text("Note")
    state                   = fields.Selection(selection=[('draft', 'New'), ('imported', 'Imported'), ('confirm', 'Ready for Invoice'), ('invoiced', 'Invoiced')], string='Status',  copy=False, default='draft', index=False, readonly=False, track_visibility='always',)

    @api.multi
    def create_invoice(self):
        invoice_obj         = self.env['account.invoice']
        invoice_line_obj    = self.env['account.invoice.line']
        journal_id          = invoice_obj.with_context({'type': 'in_invoice'}).default_get(['journal_id'])['journal_id']
        invoices_list       = []
        if self.partner_id and self.partner_id.id in [x.partner_id.id for x in self.to_invoice_ids]:
            new_invoice = invoice_obj.create({
                'partner_id'    : self.partner_id and self.partner_id.id or False,
                'account_id'    : self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id or False,
                'journal_id'    : journal_id,
                'reference'     : self.name,
                'type'          : 'in_invoice',
                'date_invoice'  : self.date_invoice,
                'currency_id'   : self.company_id.currency_id.id,
                'company_id'    : self.company_id.id,
            })
            if new_invoice:
                invoices_list.append(new_invoice.id)
                for inv_line in self.to_invoice_ids:
                    if inv_line.partner_id.id == self.partner_id.id:
                        new_line = invoice_line_obj.create({
                            'invoice_id'                : new_invoice.id,
                            'name'                      : inv_line.name or "",
                            'account_location_type_id'  : inv_line.location_type_id and inv_line.location_type_id.id or False,
                            'account_location_id'       : inv_line.location_id and inv_line.location_id.id or False,
                            'account_id'                : inv_line.account_id and inv_line.account_id.id or False,
                            'quantity'                  : 1,
                            'price_unit'                : inv_line.value,
                        })
                        inv_line.write({
                            'invoice_id'        : new_invoice.id,
                            'invoice_line_id'   : new_line.id
                        })
        if self.partner_kesehatan and self.partner_kesehatan.id in [x.partner_id.id for x in self.to_invoice_ids]:
            new_invoice = invoice_obj.create({
                'partner_id'    : self.partner_kesehatan and self.partner_kesehatan.id or False,
                'account_id'    : self.partner_kesehatan.property_account_payable_id and self.partner_kesehatan.property_account_payable_id.id or False,
                'journal_id'    : journal_id,
                'reference'     : self.name,
                'type'          : 'in_invoice',
                'date_invoice'  : self.date_invoice,
                'currency_id'   : self.company_id.currency_id.id,
                'company_id'    : self.company_id.id,
            })
            if new_invoice:
                invoices_list.append(new_invoice.id)
                for inv_line in self.to_invoice_ids:
                    if inv_line.partner_id.id == self.partner_kesehatan.id:
                        new_line = invoice_line_obj.create({
                            'invoice_id'                : new_invoice.id,
                            'name'                      : inv_line.name or "",
                            'account_location_type_id'  : inv_line.location_type_id and inv_line.location_type_id.id or False,
                            'account_location_id'       : inv_line.location_id and inv_line.location_id.id or False,
                            'account_id'                : inv_line.account_id and inv_line.account_id.id or False,
                            'quantity'                  : 1,
                            'price_unit'                : inv_line.value,
                        })
                        inv_line.write({
                            'invoice_id'        : new_invoice.id,
                            'invoice_line_id'   : new_line.id
                        })
        if self.partner_ketenagakerjaan and self.partner_ketenagakerjaan.id in [x.partner_id.id for x in self.to_invoice_ids]:
            new_invoice = invoice_obj.create({
                'partner_id'    : self.partner_ketenagakerjaan and self.partner_ketenagakerjaan.id or False,
                'account_id'    : self.partner_ketenagakerjaan.property_account_payable_id and self.partner_ketenagakerjaan.property_account_payable_id.id or False,
                'journal_id'    : journal_id,
                'reference'     : self.name,
                'type'          : 'in_invoice',
                'date_invoice'  : self.date_invoice,
                'currency_id'   : self.company_id.currency_id.id,
                'company_id'    : self.company_id.id,
            })
            if new_invoice:
                invoices_list.append(new_invoice.id)
                for inv_line in self.to_invoice_ids:
                    if inv_line.partner_id.id == self.partner_ketenagakerjaan.id:
                        new_line = invoice_line_obj.create({
                            'invoice_id'                : new_invoice.id,
                            'name'                      : inv_line.name or "",
                            'account_location_type_id'  : inv_line.location_type_id and inv_line.location_type_id.id or False,
                            'account_location_id'       : inv_line.location_id and inv_line.location_id.id or False,
                            'account_id'                : inv_line.account_id and inv_line.account_id.id or False,
                            'quantity'                  : 1,
                            'price_unit'                : inv_line.value,
                        })
                        inv_line.write({
                            'invoice_id'        : new_invoice.id,
                            'invoice_line_id'   : new_line.id
                        })
        if self.partner_pensiun and self.partner_pensiun.id in [x.partner_id.id for x in self.to_invoice_ids]:
            new_invoice = invoice_obj.create({
                'partner_id'    : self.partner_pensiun and self.partner_pensiun.id or False,
                'account_id'    : self.partner_pensiun.property_account_payable_id and self.partner_pensiun.property_account_payable_id.id or False,
                'journal_id'    : journal_id,
                'reference'     : self.name,
                'type'          : 'in_invoice',
                'date_invoice'  : self.date_invoice,
                'currency_id'   : self.company_id.currency_id.id,
                'company_id'    : self.company_id.id,
            })
            if new_invoice:
                invoices_list.append(new_invoice.id)
                for inv_line in self.to_invoice_ids:
                    if inv_line.partner_id.id == self.partner_pensiun.id:
                        new_line = invoice_line_obj.create({
                            'invoice_id'                : new_invoice.id,
                            'name'                      : inv_line.name or "",
                            'account_location_type_id'  : inv_line.location_type_id and inv_line.location_type_id.id or False,
                            'account_location_id'       : inv_line.location_id and inv_line.location_id.id or False,
                            'account_id'                : inv_line.account_id and inv_line.account_id.id or False,
                            'quantity'                  : 1,
                            'price_unit'                : inv_line.value,
                        })
                        inv_line.write({
                            'invoice_id'        : new_invoice.id,
                            'invoice_line_id'   : new_line.id
                        })
        if self.partner_keselamatan and self.partner_keselamatan.id in [x.partner_id.id for x in self.to_invoice_ids]:
            new_invoice = invoice_obj.create({
                'partner_id'    : self.partner_keselamatan and self.partner_keselamatan.id or False,
                'account_id'    : self.partner_keselamatan.property_account_payable_id and self.partner_keselamatan.property_account_payable_id.id or False,
                'journal_id'    : journal_id,
                'reference'     : self.name,
                'type'          : 'in_invoice',
                'date_invoice'  : self.date_invoice,
                'currency_id'   : self.company_id.currency_id.id,
                'company_id'    : self.company_id.id,
            })
            if new_invoice:
                invoices_list.append(new_invoice.id)
                for inv_line in self.to_invoice_ids:
                    if inv_line.partner_id.id == self.partner_keselamatan.id:
                        new_line = invoice_line_obj.create({
                            'invoice_id'                : new_invoice.id,
                            'name'                      : inv_line.name or "",
                            'account_location_type_id'  : inv_line.location_type_id and inv_line.location_type_id.id or False,
                            'account_location_id'       : inv_line.location_id and inv_line.location_id.id or False,
                            'account_id'                : inv_line.account_id and inv_line.account_id.id or False,
                            'quantity'                  : 1,
                            'price_unit'                : inv_line.value,
                        })
                        inv_line.write({
                            'invoice_id'        : new_invoice.id,
                            'invoice_line_id'   : new_line.id
                        })
        if invoices_list <> []:
            self.state = 'invoiced'
            action      = self.env.ref('account.action_invoice_tree1').read()[0]
            if len(invoices_list) > 1:
                action['domain'] = [('id', 'in', invoices_list)]
            elif len(invoices_list) == 1:
                action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
                action['res_id'] = invoices_list[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action



    @api.multi
    def unlink(self):
        for recap in self:
            if recap.state not in ('draft'):
                raise exceptions.UserError(_('You can not delete a recap document when state not in draft!'))
        return super(hr_attendance_recap, self).unlink()

    def reimport_recap(self):
        if self.line_ids:
            for lines in self.line_ids:
                lines.unlink()
        if self.book:
            self.book = False
        self.state = 'draft'

    def confirm(self):
        preparing_query = """select 
                            alt.id AS location_type
                            , al.id AS location 
                            , aa_salary.id AS salary
                            , aa_overtime.id AS overtime
                            , aa_incentive.id AS incentive
                            , aa_holiday.id AS holiday_allowance
                            , aa_kesehatan.id AS kesehatan_allowance
                            , aa_ketenagakerjaan.id AS ketenagakerjaan_allowance
                            , aa_pensiun.id AS pensiun_allowance
                            , aa_keselamatan.id AS keselamatan_allowance
                            , aa_food_transport.id AS food_transport_allowance
                            , aa_medical.id AS medical_allowance
                            , aa_welfare.id AS welfare_allowance
                            , aai_kesehatan.id AS kesehatan_allowance_inter
                            , aai_ketenagakerjaan.id AS ketenagakerjaan_allowance_inter
                            , aai_pensiun.id AS pensiun_allowance_inter
                            , aai_keselamatan.id AS keselamatan_allowance_inter
                            , sum(harl.hke_value) AS total_hke
                            , sum(harl.hkne_value) AS total_hkne
                            , sum(harl.overtime) AS total_overtime
                            , sum(harl.incentive) AS total_incentive
                            , sum(harl.food_transport_allowance) AS total_food_transport
                            , sum(harl.medical_allowance) AS total_medical
                            , sum(harl.welfare_allowance) AS total_welfare
                            -- Potongan BPJS--
                            , sum(harl.bpjs_kesehatan_wage_cut) AS kesehatan_wage_cut
                            , sum(harl.bpjs_tenaga_kerja_wage_cut) AS ketenagakerjaan_wage_cut
                            , sum(harl.bpjs_pensiun_wage_cut) AS pensiun_wage_cut
                            -- Tunjangan BPJS-- 
                            , sum(harl.safety_allowance) AS total_safety
                            , sum(harl.bpjs_tenaga_kerja_allowance) AS total_tenagakerja_allowance
                            , sum(harl.bpjs_pensiun_allowance) AS total_pensiun_allowance
                            , sum(harl.bpjs_kesehatan_allowance) AS total_kesehatan_allowance
                            -- Potongan Lainnya --
                            , sum(harl.wage_cut) as total_potongan
                            from hr_attendance_recap_line harl
                            INNER JOIN hr_attendance_recap har On har.id = harl.recap_id
                            INNER JOIN hr_employee he ON he.id = harl.employee_id
                            LEFT OUTER JOIN account_location_type alt ON alt.id = harl.location_type_id
                            LEFT OUTER JOIN account_location al ON al.id = harl.location_id
                            LEFT OUTER JOIN account_account aa_salary ON aa_salary.id = harl.account_salary_id
                            LEFT OUTER JOIN account_account aa_overtime ON aa_overtime.id = harl.account_overtime_id
                            LEFT OUTER JOIN account_account aa_incentive ON aa_incentive.id = harl.account_incentive_id
                            LEFT OUTER JOIN account_account aa_holiday ON aa_holiday.id = harl.account_holiday_allowance_id
                            LEFT OUTER JOIN account_account aa_kesehatan ON aa_kesehatan.id = harl.account_bpjs_allowance_id
                            LEFT OUTER JOIN account_account aa_ketenagakerjaan ON aa_ketenagakerjaan.id = harl.account_ketenagakerjaan_allowance_id
                            LEFT OUTER JOIN account_account aa_pensiun ON aa_pensiun.id = harl.account_pensiun_allowance_id
                            LEFT OUTER JOIN account_account aa_keselamatan ON aa_keselamatan.id = harl.account_keselamatan_allowance_id
                            LEFT OUTER JOIN account_account aa_food_transport ON aa_food_transport.id = harl.account_food_transport_allowance_id
                            LEFT OUTER JOIN account_account aa_medical ON aa_medical.id = harl.account_medical_allowance_id
                            LEFT OUTER JOIN account_account aa_welfare ON aa_welfare.id = harl.account_welfare_allowance_id
                            LEFT OUTER JOIN account_account aai_kesehatan ON aai_kesehatan.id = he.inter_account_bpjs_allowance_id
                            LEFT OUTER JOIN account_account aai_ketenagakerjaan ON aai_ketenagakerjaan.id = he.inter_account_ketenagakerjaan_allowance_id
                            LEFT OUTER JOIN account_account aai_keselamatan ON aai_keselamatan.id = he.inter_account_keselamatan_allowance_id
                            LEFT OUTER JOIN account_account aai_pensiun ON aai_pensiun.id = he.inter_account_pensiun_allowance_id
                            WHERE har.id = %s
                            GROUP BY alt.id, al.id, aa_salary.id, aa_overtime.id, aa_incentive.id, aa_holiday.id
                            , aa_kesehatan.id, aa_ketenagakerjaan.id, aa_pensiun.id, aa_keselamatan.id, aa_food_transport.id
                            , aa_medical.id, aa_welfare.id, aai_kesehatan.id, aai_ketenagakerjaan.id, aai_pensiun.id, aai_keselamatan.id;"""
        self.env.cr.execute(preparing_query % (self.id))
        preparing = self.env.cr.dictfetchall()
        na_location_type = self.env['account.location.type'].search([('code', '=', '-')])[-1].id
        total_potongan_kesehatan = 0
        total_potongan_ketenagakerjaan = 0
        total_potongan_pensiun = 0
        total_tunjangan_kesehatan = 0
        total_tunjangan_ketenagakerjaan = 0
        total_tunjangan_pensiun = 0
        inter_acc_kesehatan = False
        inter_acc_ketenagakerjaan = False
        inter_acc_pensiun = False
        for line in preparing:
            if line['ketenagakerjaan_allowance'] and line['location_type'] and line['location']:
                total_tunjangan_ketenagakerjaan += line['total_tenagakerja_allowance']
                total_potongan_ketenagakerjaan += line['ketenagakerjaan_wage_cut']
                if line['ketenagakerjaan_allowance_inter']:
                    inter_acc_ketenagakerjaan = line['ketenagakerjaan_allowance_inter']
            if line['kesehatan_allowance'] and line['location_type'] and line['location']:
                total_potongan_kesehatan += line['kesehatan_wage_cut']
                total_tunjangan_kesehatan += line['total_kesehatan_allowance']
                if line['kesehatan_allowance_inter']:
                    inter_acc_kesehatan = line['kesehatan_allowance_inter']
            if line['pensiun_allowance'] and line['location_type'] and line['location']:
                total_potongan_pensiun += line['pensiun_wage_cut']
                total_tunjangan_pensiun += line['total_pensiun_allowance']
                if line['pensiun_allowance_inter']:
                    inter_acc_pensiun = line['pensiun_allowance_inter']
            if self.partner_keselamatan:
                if line['keselamatan_allowance'] and line['location_type'] and line['location']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'JKK + JKM',
                        'partner_id': self.partner_keselamatan and self.partner_keselamatan.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['keselamatan_allowance'],
                        'value': line['total_safety']
                    })
            if self.partner_kesehatan:
                if line['kesehatan_allowance'] and line['location_type'] and line['location'] and (
                        line['kesehatan_wage_cut'] or line['total_kesehatan_allowance']):
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'BPJS Kesehatan',
                        'partner_id': self.partner_kesehatan and self.partner_kesehatan.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['kesehatan_allowance'],
                        # 'value'             : line['total_kesehatan_allowance'] - line['kesehatan_wage_cut']
                        'value': line['total_kesehatan_allowance']
                    })
            if self.partner_ketenagakerjaan:
                if line['ketenagakerjaan_allowance'] and line['location_type'] and line['location'] and (
                        line['ketenagakerjaan_wage_cut'] or line['total_tenagakerja_allowance']):
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'BPJS Ketenagakerjaan',
                        'partner_id': self.partner_ketenagakerjaan and self.partner_ketenagakerjaan.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['ketenagakerjaan_allowance'],
                        # 'value'             : line['total_tenagakerja_allowance'] - line['ketenagakerjaan_wage_cut']
                        'value': line['total_tenagakerja_allowance']
                    })
            if self.partner_pensiun:
                if line['pensiun_allowance'] and line['location_type'] and line['location'] and (
                        line['total_pensiun_allowance'] or line['pensiun_wage_cut']):
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'BPJS Pensiun',
                        'partner_id': self.partner_pensiun and self.partner_pensiun.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['pensiun_allowance'],
                        # 'value'             : line['total_pensiun_allowance'] - line['total_pensiun_allowance']
                        'value': line['total_pensiun_allowance']
                    })
            if self.partner_id:
                if line['salary'] and line['location_type'] and line['location'] and line['total_hke']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Gaji HKE',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['salary'],
                        'value': line['total_hke'] - line['total_potongan'],
                    })
                if line['salary'] and line['location_type'] and line['location'] and line['total_hkne']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Gaji HKNE',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['salary'],
                        'value': line['total_hkne'],
                    })
                if line['overtime'] and line['location_type'] and line['location'] and line['total_overtime']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Lembur',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['overtime'],
                        'value': line['total_overtime'],
                    })
                # if line['holiday_allowance'] and line['location_type'] and line['location']:
                #     self.env['hr.attendance.recap.to.invoice.line'].create({
                #         'name'              : 'THR',
                #         'partner_id'        : self.partner_id and self.partner_id.id or False,
                #         'recap_id'          : self.id,
                #         'location_type_id'  : line['location_type'],
                #         'location_id'       : line['location'],
                #         'account_id'        : line['holiday_allowance'],
                #     })
                if line['incentive'] and line['location_type'] and line['location'] and line['total_incentive']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Insentif',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['incentive'],
                        'value': line['total_incentive'],
                    })
                if line['food_transport_allowance'] and line['location_type'] and line['location'] and line[
                    'total_food_transport']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Tunjangan Makan dan Transport',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['food_transport_allowance'],
                        'value': line['total_food_transport'],
                    })
                if line['medical_allowance'] and line['location_type'] and line['location'] and line['total_medical']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Tunjangan Pengobatan',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['medical_allowance'],
                        'value': line['total_medical'],
                    })
                if line['welfare_allowance'] and line['location_type'] and line['location'] and line['total_welfare']:
                    self.env['hr.attendance.recap.to.invoice.line'].create({
                        'name': 'Tunjangan Kesejahteraan',
                        'partner_id': self.partner_id and self.partner_id.id or False,
                        'recap_id': self.id,
                        'location_type_id': line['location_type'],
                        'location_id': line['location'],
                        'account_id': line['welfare_allowance'],
                        'value': line['total_welfare'],
                    })
        if inter_acc_kesehatan and total_potongan_kesehatan:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Kesehatan',
                'partner_id': self.partner_id and self.partner_id.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_kesehatan,
                'value': -(total_potongan_kesehatan - total_tunjangan_kesehatan),
            })
        if inter_acc_kesehatan and total_potongan_kesehatan:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Kesehatan',
                'partner_id': self.partner_kesehatan and self.partner_kesehatan.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_kesehatan,
                'value': (total_potongan_kesehatan - total_tunjangan_kesehatan),
            })
        if inter_acc_ketenagakerjaan and total_potongan_ketenagakerjaan:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Ketenagakerjaan',
                'partner_id': self.partner_id and self.partner_id.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_ketenagakerjaan,
                'value': -(total_potongan_ketenagakerjaan - total_tunjangan_ketenagakerjaan),
            })
        if inter_acc_ketenagakerjaan and total_potongan_ketenagakerjaan:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Ketenagakerjaan',
                'partner_id': self.partner_ketenagakerjaan and self.partner_ketenagakerjaan.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_ketenagakerjaan,
                'value': (total_potongan_ketenagakerjaan - total_tunjangan_ketenagakerjaan),
            })
        if inter_acc_pensiun and total_potongan_pensiun:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Pensiun',
                'partner_id': self.partner_id and self.partner_id.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_pensiun,
                'value': -(total_potongan_pensiun - total_tunjangan_pensiun),
            })
        if inter_acc_pensiun and total_potongan_pensiun:
            self.env['hr.attendance.recap.to.invoice.line'].create({
                'name': 'Potongan Tunjangan Pensiun',
                'partner_id': self.partner_pensiun and self.partner_pensiun.id or False,
                'recap_id': self.id,
                'location_type_id': na_location_type,
                'location_id': False,
                'account_id': inter_acc_pensiun,
                'value': (total_potongan_pensiun - total_tunjangan_pensiun),
            })

        self.state = 'confirm'
        self.date_invoice = datetime.datetime.now()

    def back(self):
        if self.to_invoice_ids:
            for unlink in self.to_invoice_ids:
                unlink.unlink()
        self.state = 'imported'

    @api.multi
    def action_view_invoice(self):
        invoices    = [x.invoice_id.id for x in self.to_invoice_ids]
        action      = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def import_recap(self):
        """
        XL_CELL_EMPTY	0	empty string ‘’
        XL_CELL_TEXT	1	a Unicode string
        XL_CELL_NUMBER	2	float
        XL_CELL_DATE	3	float
        XL_CELL_BOOLEAN	4	int; 1 means True, 0 means False
        XL_CELL_ERROR	5	int representing internal Excel codes; for a text representation, refer to the supplied dictionary error_text_from_code
        XL_CELL_BLANK	6	empty string ‘’. Note: this type will appear only when open_workbook(..., formatting_info= True) is used.
        """
        self.error_note = ""
        attendance_recap_line_obj  = self.env['hr.attendance.recap.line']
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
        error_note  = ""
        for i in range(total_sheet):
            sheet       = wb.sheet_by_index(i)
            for rows in range(sheet.nrows):
                #Rows 1 dan 2 hanya untuk title
                if rows > 1:
                    employee_id                 = False
                    hke                         = 0.00
                    hkne                        = 0.00
                    hk_total                    = 0.00
                    hke_value                   = 0.00
                    hkne_value                  = 0.00
                    hk_value_total              = 0.00
                    wage                        = 0.00
                    overtime                    = 0.00
                    incentive                   = 0.00
                    food_transport_allowance    = 0.00
                    holiday_allowance           = 0.00
                    medical_allowance           = 0.00
                    welfare_allowance           = 0.00
                    safety_allowance            = 0.00
                    bpjs_tenaga_kerja_allowance = 0.00
                    bpjs_pensiun_allowance      = 0.00
                    bpjs_kesehatan_allowance    = 0.00
                    gross_salary                = 0.00
                    bpjs_tenaga_kerja_wage_cut  = 0.00
                    bpjs_pensiun_wage_cut       = 0.00
                    bpjs_kesehatan_wage_cut     = 0.00
                    cooperative_wage_cut        = 0.00
                    tax_wage_cut                = 0.00
                    wage_cut                    = 0.00
                    total_wage_cut              = 0.00
                    net_salary                  = 0.00
                    location_id                 = False
                    location_type_id            = False
                    for j in range(sheet.ncols):
                        if j == 0:
                            if "." in str(sheet.cell_value(rows, j)):
                                employee_ids = self.env['hr.employee'].search([('no_induk', '=', str(sheet.cell_value(rows, j)).split('.')[0])])
                            else:
                                employee_ids = self.env['hr.employee'].search([('no_induk', '=', str(sheet.cell_value(rows, j)))])
                            if len(employee_ids) > 1:
                                employee_id = employee_ids[-1]
                            elif len(employee_ids) == 0:
                                if not error_note:
                                    error_note          = "NIK Karyawan : " + str(sheet.cell_value(rows, 1)) + " belum diisi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNIK Karyawan : " + str(sheet.cell_value(rows, 1)) + " belum diisi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                            else:
                                employee_id = employee_ids
                        if j == 2:
                            hke                         = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 3:
                            hkne                        = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 4:
                            hk_total                    = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 5:
                            hke_value                   = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 6:
                            hkne_value                  = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 7:
                            hk_value_total              = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 8:
                            wage                        = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 9:
                            overtime                    = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 10:
                            incentive                   = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.incentive and incentive <> 0:
                                if not error_note:
                                    error_note          = "Nilai Insentif :" + str(incentive) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Insentif, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Insentif :" + str(incentive) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Insentif, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 11:
                            food_transport_allowance    = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.food_transport and food_transport_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai Tunjangan Makan & Transport :" + str(food_transport_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Makan & Transport, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Tunjangan Makan & Transport :" + str(food_transport_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Makan & Transport, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 12:
                            holiday_allowance           = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 13:
                            medical_allowance           = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.medical and medical_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai Tunjangan Pengobatan :" + str(medical_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Pengobatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Tunjangan Pengobatan :" + str(medical_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Pengobatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 14:
                            welfare_allowance           = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.welfare and welfare_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai Tunjangan Kesejahteraan :" + str(welfare_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Kesejahteraan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Tunjangan Kesejahteraan :" + str(welfare_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan Kesejahteraan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 15:
                            safety_allowance            = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.keselamatan and safety_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai Tunjangan JKK + JKM :" + str(safety_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan JKK + JKM, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Tunjangan JKK + JKM :" + str(safety_allowance) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan JKK + JKM, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 16:
                            bpjs_tenaga_kerja_allowance = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.ketenagakerjaan and bpjs_tenaga_kerja_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai BPJS Ketenagakerjaan :" + str(bpjs_tenaga_kerja_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Ketenagakerjaan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai BPJS Ketenagakerjaan :" + str(bpjs_tenaga_kerja_allowance) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Ketenagakerjaan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 17:
                            bpjs_pensiun_allowance      = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.pensiun and bpjs_pensiun_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai BPJS Pensiun :" + str(bpjs_pensiun_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Pensiun, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai BPJS Pensiun :" + str(bpjs_pensiun_allowance) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Pensiun, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 18:
                            bpjs_kesehatan_allowance    = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.kesehatan and bpjs_kesehatan_allowance <> 0:
                                if not error_note:
                                    error_note          = "Nilai BPJS Kesehatan :" + str(bpjs_kesehatan_allowance) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Kesehatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai BPJS Kesehatan :" + str(bpjs_kesehatan_allowance) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Kesehatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 19:
                            gross_salary                = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 20:
                            bpjs_tenaga_kerja_wage_cut  = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.ketenagakerjaan and bpjs_tenaga_kerja_wage_cut <> 0:
                                if not error_note:
                                    error_note          = "Nilai Potongan Ketenagakerjaan :" + str(bpjs_tenaga_kerja_wage_cut) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Ketenagakerjaan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Potongan Ketenagakerjaan :" + str(bpjs_tenaga_kerja_wage_cut) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Ketenagakerjaan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 21:
                            bpjs_pensiun_wage_cut       = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.pensiun and bpjs_pensiun_wage_cut <> 0:
                                if not error_note:
                                    error_note          = "Nilai Potongan Pensiun :" + str(bpjs_pensiun_wage_cut) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Pensiun, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Potongan Pensiun :" + str(bpjs_pensiun_wage_cut) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Pensiun, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 22:
                            bpjs_kesehatan_wage_cut     = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                            if employee_id and not employee_id.kesehatan and bpjs_kesehatan_wage_cut <> 0:
                                if not error_note:
                                    error_note          = "Nilai Potongan Kesehatan :" + str(bpjs_kesehatan_wage_cut) + ". Karyawan : " + str(employee_id.name) + " tidak berhak mendapatkan Tunjangan BPJS Kesehatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                                else:
                                    error_note          = error_note + "\nNilai Potongan Kesehatan :" + str(bpjs_kesehatan_wage_cut) + ". Karyawan : " + str(employee_id.name) + " Tidak berhak mendapatkan Tunjangan BPJS Kesehatan, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        if j == 23:
                            cooperative_wage_cut        = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 24:
                            tax_wage_cut                = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 25:
                            wage_cut                    = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 26:
                            total_wage_cut              = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 27:
                            net_salary                  = 0 if str(sheet.cell_value(rows, j)) == '' else float(sheet.cell_value(rows, j))
                        if j == 28:
                            if "." in str(sheet.cell_value(rows, j)):
                                location_type_ids = self.env['account.location.type'].search([('code', '=', str(sheet.cell_value(rows, j)).split('.')[0])])
                            else:
                                location_type_ids = self.env['account.location.type'].search([('code', '=', str(sheet.cell_value(rows, j)))])
                            if len(location_type_ids) > 1:
                                location_type_id = location_type_ids[-1]
                            else:
                                location_type_id = location_type_ids
                        if j == 29:
                            if "." in str(sheet.cell_value(rows, j)):
                                location_ids = self.env['account.location'].search([('code', '=', str(sheet.cell_value(rows, j)).split('.')[0])])
                            else:
                                location_ids = self.env['account.location'].search([('code', '=', str(sheet.cell_value(rows, j)))])
                            if len(location_ids) > 1:
                                location_id = location_ids[-1]
                            else:
                                location_id = location_ids

                    if employee_id and not location_id and not employee_id.default_location_id:
                        if not error_note:
                            error_note          = "Karyawan : " + str(employee_id.name) + " tidak memiliki default lokasi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        else:
                            error_note          = error_note + "\nKaryawan : " + str(employee_id.name) + " tidak memiliki default lokasi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."

                    if employee_id and employee_id.default_location_id and not employee_id.default_location_id.default_salary_account_id and not employee_id.default_account_salary_id:
                        if not error_note:
                            error_note          = "Karyawan : " + str(employee_id.name) + " tidak memiliki default akun gaji, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        else:
                            error_note          = error_note + "\nKaryawan : " + str(employee_id.name) + " tidak memiliki default akun gaji, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."

                    if employee_id and not location_type_id and not employee_id.default_location_type_id:
                        if not error_note:
                            error_note          = "Karyawan : " + str(employee_id.name) + " tidak memiliki default tipe lokasi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."
                        else:
                            error_note          = error_note + "\nKaryawan : " + str(employee_id.name) + " tidak memiliki default tipe lokasi, edit di file excel baris ke : " + str((rows + 1)) + " atau edit master data karyawan."

                    if employee_id:
                        attendance_recap_line_obj.create({
                            'recap_id'                              : self.id,
                            'name'                                  : employee_id.no_induk or False,
                            'employee_id'                           : employee_id.id or False,
                            'wage'                                  : wage,
                            'overtime'                              : overtime,
                            'incentive'                             : incentive,
                            'food_transport_allowance'              : food_transport_allowance,
                            'holiday_allowance'                     : holiday_allowance,
                            'medical_allowance'                     : medical_allowance,
                            'welfare_allowance'                     : welfare_allowance,
                            'safety_allowance'                      : safety_allowance,
                            'gross_salary'                          : gross_salary,
                            'net_salary'                            : net_salary,
                            'hke'                                   : hke,
                            'hkne'                                  : hkne,
                            'hk_total'                              : hk_total,
                            'hke_value'                             : hke_value,
                            'hkne_value'                            : hkne_value,
                            'hk_value_total'                        : hk_value_total,
                            'bpjs_tenaga_kerja_allowance'           : bpjs_tenaga_kerja_allowance,
                            'bpjs_pensiun_allowance'                : bpjs_pensiun_allowance,
                            'bpjs_kesehatan_allowance'              : bpjs_kesehatan_allowance,
                            'bpjs_tenaga_kerja_wage_cut'            : bpjs_tenaga_kerja_wage_cut,
                            'bpjs_pensiun_wage_cut'                 : bpjs_pensiun_wage_cut,
                            'bpjs_kesehatan_wage_cut'               : bpjs_kesehatan_wage_cut,
                            'cooperative_wage_cut'                  : cooperative_wage_cut,
                            'tax_wage_cut'                          : tax_wage_cut,
                            'wage_cut'                              : wage_cut,
                            'total_wage_cut'                        : total_wage_cut + holiday_allowance,
                            'account_salary_id'                     : (location_id.default_salary_account_id and location_id.default_salary_account_id.id) or (employee_id.default_account_salary_id and employee_id.default_account_salary_id.id),
                            'location_type_id'                      : (location_type_id and location_type_id.id) or (employee_id.default_location_type_id and employee_id.default_location_type_id.id),
                            'location_id'                           : (location_id and location_id.id or False) or (employee_id.default_location_id and employee_id.default_location_id.id),
                            'account_overtime_id'                   : employee_id.default_account_overtime_id and employee_id.default_account_overtime_id.id  or False,
                            'account_incentive_id'                  : employee_id.default_account_incentive_id and employee_id.default_account_incentive_id.id or False,
                            'account_holiday_allowance_id'          : employee_id.default_account_holiday_allowance_id and employee_id.default_account_holiday_allowance_id.id or False,
                            'account_bpjs_allowance_id'             : employee_id.default_account_bpjs_allowance_id and employee_id.default_account_bpjs_allowance_id.id or False,
                            'account_ketenagakerjaan_allowance_id'  : employee_id.default_account_ketenagakerjaan_allowance_id and employee_id.default_account_ketenagakerjaan_allowance_id.id or False,
                            'account_pensiun_allowance_id'          : employee_id.default_account_pensiun_allowance_id and employee_id.default_account_pensiun_allowance_id.id or False,
                            'account_keselamatan_allowance_id'      : employee_id.default_account_keselamatan_allowance_id and employee_id.default_account_keselamatan_allowance_id.id or False,
                            'account_food_transport_allowance_id'   : employee_id.default_account_food_transport_allowance_id and employee_id.default_account_food_transport_allowance_id.id or False,
                            'account_medical_allowance_id'          : employee_id.default_account_medical_allowance_id and employee_id.default_account_medical_allowance_id.id or False,
                            'account_welfare_allowance_id'          : employee_id.default_account_welfare_allowance_id and employee_id.default_account_welfare_allowance_id.id or False,
                        })
        self.error_note = error_note
        if self.line_ids and self.error_note == '':
            self.state      = 'imported'
            if self.name == '/':
                self.name   = self.env['ir.sequence'].next_by_code('hr.attendance.recap.sequence.number') or _('New')

class hr_attendance_recap_line(models.Model):
    _name           = 'hr.attendance.recap.line'
    _description    = 'Attendance Recap Line'

    name                                    = fields.Char("NIK")
    recap_id                                = fields.Many2one('hr.attendance.recap', string="Recap", ondelete="cascade")
    employee_id                             = fields.Many2one('hr.employee', string="Nama")
    hke                                     = fields.Float("HKE")
    hkne                                    = fields.Float("HKNE")
    hk_total                                = fields.Float("Total")
    hke_value                               = fields.Float("HKE")
    hkne_value                              = fields.Float("HKNE")
    hk_value_total                          = fields.Float("Total")
    wage                                    = fields.Float("Gaji Pokok")
    overtime                                = fields.Float("Gaji Lembur")
    incentive                               = fields.Float("Gaji Insentif")
    food_transport_allowance                = fields.Float("Transport dan Makan")
    holiday_allowance                       = fields.Float("THR")
    medical_allowance                       = fields.Float("Pengobatan")
    welfare_allowance                       = fields.Float("Kesejahteraan")
    safety_allowance                        = fields.Float("JKK + JKM")
    bpjs_tenaga_kerja_allowance             = fields.Float("BPJS Tenaga Kerja")
    bpjs_pensiun_allowance                  = fields.Float("BPJS Pensiun")
    bpjs_kesehatan_allowance                = fields.Float("BPJS Kesehatan")
    gross_salary                            = fields.Float("Gaji Bruto")
    bpjs_tenaga_kerja_wage_cut              = fields.Float("BPJS Tenaga Kerja")
    bpjs_pensiun_wage_cut                   = fields.Float("BPJS Pensiun")
    bpjs_kesehatan_wage_cut                 = fields.Float("BPJS Kesehatan")
    cooperative_wage_cut                    = fields.Float("Koperasi")
    tax_wage_cut                            = fields.Float("PPh 21")
    wage_cut                                = fields.Float("Potongan")
    total_wage_cut                          = fields.Float("Total Potongan")
    net_salary                              = fields.Float("Gaji Bersih")
    location_type_id                        = fields.Many2one('account.location.type', string="Tipe Lokasi", ondelete="restrict")
    location_id                             = fields.Many2one('account.location', string="Lokasi", ondelete="restrict")
    account_salary_id                       = fields.Many2one('account.account', string="Gaji", ondelete="restrict")
    account_overtime_id                     = fields.Many2one('account.account', string='Lembur', ondelete="restrict")
    account_incentive_id                    = fields.Many2one('account.account', string='Insentif', ondelete="restrict")
    account_holiday_allowance_id            = fields.Many2one('account.account', string='THR ', ondelete="restrict")
    account_bpjs_allowance_id               = fields.Many2one('account.account', string='Kesehatan', ondelete="restrict")
    account_ketenagakerjaan_allowance_id    = fields.Many2one('account.account', string='Ketenagakerjaan', ondelete="restrict")
    account_pensiun_allowance_id            = fields.Many2one('account.account', string='Pensiun', ondelete="restrict")
    account_keselamatan_allowance_id        = fields.Many2one('account.account', string='JKK + JKM', ondelete="restrict")
    account_food_transport_allowance_id     = fields.Many2one('account.account', string='Transport & Makan', ondelete="restrict")
    account_medical_allowance_id            = fields.Many2one('account.account', string='Pengobatan', ondelete="restrict")
    account_welfare_allowance_id            = fields.Many2one('account.account', string='Kesejahteraan', ondelete="restrict")

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id        = False
            self.account_salary_id  = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.account_salary_id    = self.location_id and self.location_id.default_salary_account_id and self.location_id.default_salary_account_id.id or False

class hr_attendance_recap_to_invoice_line(models.Model):
    _name           = 'hr.attendance.recap.to.invoice.line'
    _description    = 'Attendance Recap Line'

    name                = fields.Char("Deskripsi")
    location_type_id    = fields.Many2one('account.location.type', string="Tipe Lokasi", ondelete="restrict")
    location_id         = fields.Many2one('account.location', string="Lokasi", ondelete="restrict")
    partner_id          = fields.Many2one('res.partner', string="Partner", ondelete="restrict")
    account_id          = fields.Many2one('account.account', string="Account", ondelete="restrict")
    invoice_id          = fields.Many2one('account.invoice', string="Account Invoice", ondelete="restrict")
    invoice_line_id     = fields.Many2one('account.invoice.line', string="Account Invoice", ondelete="restrict")
    value               = fields.Float("Value")
    recap_id            = fields.Many2one('hr.attendance.recap', string="Recap", ondelete="cascade")