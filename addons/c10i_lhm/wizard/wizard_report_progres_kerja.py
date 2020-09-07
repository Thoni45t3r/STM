from odoo import models, fields, tools, api, _
from datetime import datetime
import time
import datetime

class WizardReportProgresKerjaHarian(models.TransientModel):
    _name           = "wizard.report.progres.kerja.harian"
    _description    = "Laporan Progres Pekerjaan Harian"

    name            = fields.Char(default="Laporan Progres Pekerjaan Harian")
    date_start      = fields.Date("Periode Dari Tgl", required=True)
    date_end        = fields.Date("Sampai Tgl", required=True)
    type            = fields.Selection([('harian', 'Harian')], string='Type', default='harian')
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    report_type     = fields.Selection([('xlsx', 'XLSX'), ('xls', 'XLS'), ('pdf', 'PDF'), ], string='Type', default='xlsx')
    group_ids       = fields.Many2many('plantation.location.reference', 'grouping_progress_report_rel', 'wizard_id', 'loc_ref_id', string="Grouping")

    @api.multi
    def create_report(self):
        data            = self.read()[-1]
        listing         = []
        listing         = listing + [(x.name).encode("utf-8") for x in self.group_ids]
        if listing == []:
            listing = listing + [(x.name).encode("utf-8") for x in self.env['plantation.location.reference'].search([])]
        listing         = str(listing).replace('[', '').replace(']', '')
        if self.report_type == 'pdf':
            report_type = self.report_type
            report_name = 'report_progres_kerja_harian_pdf'
        else:
            report_type = self.report_type
            report_name = 'report_progres_kerja_harian'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'wizard.report.progres.kerja.harian',
                'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type'   : report_type,
                'form'          : data,
                'listing'       : listing.replace("'",'').replace(",", ", "),
                'user_print'    : self.env.user.partner_id.name,
            },
            'nodestroy'     : False
        }

class WizardReportProgresKerjaMaterialDetail(models.TransientModel):
    _name           = "wizard.report.progres.kerja.material.detail"
    _description    = "Laporan Progres Pekerjaan Harian Material Detail"

    name            = fields.Char(default="Laporan Progres Pekerjaan Harian Material Detail")
    date_start      = fields.Date("Periode Dari Tgl", required=True)
    date_end        = fields.Date("Sampai Tgl", required=True)
    type            = fields.Selection([('harian', 'Harian')], string='Type', default='harian')
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    report_type     = fields.Selection([('xlsx', 'XLSX'), ('xls', 'XLS')], string='Type', default='xlsx')
    group_ids       = fields.Many2many('plantation.location.reference', 'grouping_progress_report_material_rel', 'wizard_id', 'loc_ref_id', string="Grouping")

    @api.multi
    def create_report(self):
        data            = self.read()[-1]
        listing         = []
        listing         = listing + [(x.name).encode("utf-8") for x in self.group_ids]
        if listing == []:
            listing = listing + [(x.name).encode("utf-8") for x in self.env['plantation.location.reference'].search([])]
        listing         = str(listing).replace('[', '').replace(']', '')
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'report_progres_kerja_harian_material_detail',
            'datas'         : {
                'model'         : 'wizard.report.progres.kerja.material.detail',
                'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type'   : data['report_type'],
                'form'          : data,
                'listing'       : listing.replace("'",'').replace(",", ", "),
                'user_print'    : self.env.user.partner_id.name,
            },
            'nodestroy'     : False
        }