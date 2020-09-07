from odoo import models, fields, tools, api, _
from datetime import datetime
import time
import datetime


class WizardReportMonitor(models.TransientModel):
    _name           = "wizard.report.monitor"
    _description    = "Monitoring DU Harian"

    @api.one
    @api.depends('user_id')
    def _compute_kemandoran(self):
        for kemandoran in self:
            if self.env.user.id == (self.env['ir.model.data'].xmlid_to_res_id('base.user_root') or 1):
                foreman_ids = self.env['hr.foreman'].search([])
                if foreman_ids:
                    kemandoran.kemandoran_ids = foreman_ids.ids
            elif kemandoran.user_id:
                foreman_ids = self.env['hr.foreman'].search([('user_input_id','=',kemandoran.user_id.id)])
                if foreman_ids:
                    kemandoran.kemandoran_ids = foreman_ids.ids

    name            = fields.Char(default="Monitoring DU Harian")
    date_start      = fields.Date("Periode Dari Tgl", required=True)
    date_end        = fields.Date("Sampai Tgl", required=True)
    kemandoran_ids  = fields.Many2many(comodel_name="hr.foreman", string="Kemandoran", ondelete="restrict", compute="_compute_kemandoran")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    user_id         = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    du_ids          = fields.One2many(comodel_name='wizard.report.monitor.du', inverse_name='monitor_id', string='Monitor Daftar Upah', copy=False)


    @api.multi
    def generate_report(self):
        # Monitor Dafatar Upah
        if self.du_ids:
            for data in self.du_ids:
                data.unlink()
        
        str_sql = """
            SELECT
            he.kemandoran_id,
            no_induk ,
            he.id ,
            sum(premi+overtime_value-penalty) AS "TP",
            sum(work_day) AS "TH",
            sum(case when EXTRACT(DAY FROM ltl.date) =1 then premi+overtime_value-penalty else 0 end) AS "1P",
            sum(case when EXTRACT(DAY FROM ltl.date) =1 then work_day else 0 end) AS "1H",
            sum(case when EXTRACT(DAY FROM ltl.date) =2 then premi+overtime_value-penalty else 0 end) AS "2P",
            sum(case when EXTRACT(DAY FROM ltl.date) =2 then work_day else 0 end) AS "2H",
            sum(case when EXTRACT(DAY FROM ltl.date) =3 then premi+overtime_value-penalty else 0 end) AS "3P",
            sum(case when EXTRACT(DAY FROM ltl.date) =3 then work_day else 0 end) AS "3H",
            sum(case when EXTRACT(DAY FROM ltl.date) =4 then premi+overtime_value-penalty else 0 end) AS "4P",
            sum(case when EXTRACT(DAY FROM ltl.date) =4 then work_day else 0 end) AS "4H",
            sum(case when EXTRACT(DAY FROM ltl.date) =5 then premi+overtime_value-penalty else 0 end) AS "5P",
            sum(case when EXTRACT(DAY FROM ltl.date) =5 then work_day else 0 end) AS "5H",
            sum(case when EXTRACT(DAY FROM ltl.date) =6 then premi+overtime_value-penalty else 0 end) AS "6P",
            sum(case when EXTRACT(DAY FROM ltl.date) =6 then work_day else 0 end) AS "6H",
            sum(case when EXTRACT(DAY FROM ltl.date) =7 then premi+overtime_value-penalty else 0 end) AS "7P",
            sum(case when EXTRACT(DAY FROM ltl.date) =7 then work_day else 0 end) AS "7H",
            sum(case when EXTRACT(DAY FROM ltl.date) =8 then premi+overtime_value-penalty else 0 end) AS "8P",
            sum(case when EXTRACT(DAY FROM ltl.date) =8 then work_day else 0 end) AS "8H" ,
            sum(case when EXTRACT(DAY FROM ltl.date) =9 then premi+overtime_value-penalty else 0 end) AS "9P",
            sum(case when EXTRACT(DAY FROM ltl.date) =9 then work_day else 0 end) AS "9H",
            sum(case when EXTRACT(DAY FROM ltl.date) =10 then premi+overtime_value-penalty else 0 end) AS "10P",
            sum(case when EXTRACT(DAY FROM ltl.date) =10 then work_day else 0 end) AS "10H",
            
            sum(case when EXTRACT(DAY FROM ltl.date) =11 then premi+overtime_value-penalty else 0 end) AS "11P",
            sum(case when EXTRACT(DAY FROM ltl.date) =11 then work_day else 0 end) AS "11H",
            sum(case when EXTRACT(DAY FROM ltl.date) =12 then premi+overtime_value-penalty else 0 end) AS "12P",
            sum(case when EXTRACT(DAY FROM ltl.date) =12 then work_day else 0 end) AS "12H",
            sum(case when EXTRACT(DAY FROM ltl.date) =13 then premi+overtime_value-penalty else 0 end) AS "13P",
            sum(case when EXTRACT(DAY FROM ltl.date) =13 then work_day else 0 end) AS "13H",
            sum(case when EXTRACT(DAY FROM ltl.date) =14 then premi+overtime_value-penalty else 0 end) AS "14P",
            sum(case when EXTRACT(DAY FROM ltl.date) =14 then work_day else 0 end) AS "14H",
            sum(case when EXTRACT(DAY FROM ltl.date) =15 then premi+overtime_value-penalty else 0 end) AS "15P",
            sum(case when EXTRACT(DAY FROM ltl.date) =15 then work_day else 0 end) AS "15H",
            sum(case when EXTRACT(DAY FROM ltl.date) =16 then premi+overtime_value-penalty else 0 end) AS "16P",
            sum(case when EXTRACT(DAY FROM ltl.date) =16 then work_day else 0 end) AS "16H",
            sum(case when EXTRACT(DAY FROM ltl.date) =17 then premi+overtime_value-penalty else 0 end) AS "17P",
            sum(case when EXTRACT(DAY FROM ltl.date) =17 then work_day else 0 end) AS "17H",
            sum(case when EXTRACT(DAY FROM ltl.date) =18 then premi+overtime_value-penalty else 0 end) AS "18P",
            sum(case when EXTRACT(DAY FROM ltl.date) =18 then work_day else 0 end) AS "18H",
            sum(case when EXTRACT(DAY FROM ltl.date) =19 then premi+overtime_value-penalty else 0 end) AS "19P",
            sum(case when EXTRACT(DAY FROM ltl.date) =19 then work_day else 0 end) AS "19H",
            sum(case when EXTRACT(DAY FROM ltl.date) =20 then premi+overtime_value-penalty else 0 end) AS "20P",
            sum(case when EXTRACT(DAY FROM ltl.date) =20 then work_day else 0 end) AS "20H",
            
            sum(case when EXTRACT(DAY FROM ltl.date) =21 then premi+overtime_value-penalty else 0 end) AS "21P",
            sum(case when EXTRACT(DAY FROM ltl.date) =21 then work_day else 0 end) AS "21H",
            sum(case when EXTRACT(DAY FROM ltl.date) =22 then premi+overtime_value-penalty else 0 end) AS "22P",
            sum(case when EXTRACT(DAY FROM ltl.date) =22 then work_day else 0 end) AS "22H",
            sum(case when EXTRACT(DAY FROM ltl.date) =23 then premi+overtime_value-penalty else 0 end) AS "23P",
            sum(case when EXTRACT(DAY FROM ltl.date) =23 then work_day else 0 end) AS "23H",
            sum(case when EXTRACT(DAY FROM ltl.date) =24 then premi+overtime_value-penalty else 0 end) AS "24P",
            sum(case when EXTRACT(DAY FROM ltl.date) =24 then work_day else 0 end) AS "24H",
            sum(case when EXTRACT(DAY FROM ltl.date) =25 then premi+overtime_value-penalty else 0 end) AS "25P",
            sum(case when EXTRACT(DAY FROM ltl.date) =25 then work_day else 0 end) AS "25H",
            sum(case when EXTRACT(DAY FROM ltl.date) =26 then premi+overtime_value-penalty else 0 end) AS "26P",
            sum(case when EXTRACT(DAY FROM ltl.date) =26 then work_day else 0 end) AS "26H",
            sum(case when EXTRACT(DAY FROM ltl.date) =27 then premi+overtime_value-penalty else 0 end) AS "27P",
            sum(case when EXTRACT(DAY FROM ltl.date) =27 then work_day else 0 end) AS "27H",
            sum(case when EXTRACT(DAY FROM ltl.date) =28 then premi+overtime_value-penalty else 0 end) AS "28P",
            sum(case when EXTRACT(DAY FROM ltl.date) =28 then work_day else 0 end) AS "28H",
            sum(case when EXTRACT(DAY FROM ltl.date) =29 then premi+overtime_value-penalty else 0 end) AS "29P",
            sum(case when EXTRACT(DAY FROM ltl.date) =29 then work_day else 0 end) AS "29H",
            sum(case when EXTRACT(DAY FROM ltl.date) =30 then premi+overtime_value-penalty else 0 end) AS "30P",
            sum(case when EXTRACT(DAY FROM ltl.date) =30 then work_day else 0 end) AS "30H",
            sum(case when EXTRACT(DAY FROM ltl.date) =31 then premi+overtime_value-penalty else 0 end) AS "31P",
            sum(case when EXTRACT(DAY FROM ltl.date) =31 then work_day else 0 end) AS "31H"
            
            FROM lhm_transaction lt
            LEFT JOIN lhm_transaction_line ltl ON lt.id=ltl.lhm_id
            LEFT JOIN hr_employee he ON he.id=ltl.employee_id
            LEFT JOIN hr_foreman hf ON hf.id=he.kemandoran_id
            where lt.date::date between %s and %s and lt.state in ('close','done','in_progress') and attendance_id is not null
            GROUP BY he.kemandoran_id, no_induk, he.id
        """

        str_sql2 = ''
        if self.kemandoran_ids:
            str_kemandoran_id = ''
            for data in self.kemandoran_ids:
                str_kemandoran_id += str(data.id)+","
            str_sql2 = ' HAVING he.kemandoran_id in ('+str_kemandoran_id[:-1]+')'

        str_sql = str_sql + str_sql2 + ' ORDER BY he.kemandoran_id, no_induk '

        self.env.cr.execute(str_sql, (self.date_start, self.date_end))
        for data in self.env.cr.fetchall():
            new_lines = {
                'Kemandoran_id': data[0],
                'nik': data[1],
                'employee_id': data[2],
                'PT': data[3],
                'HT': data[4],

                'P01': data[5],
                'H01': data[6],

                'P02': data[7],
                'H02': data[8],

                'P03': data[9],
                'H03': data[10],

                'P04': data[11],
                'H04': data[12],

                'P05': data[13],
                'H05': data[14],

                'P06': data[15],
                'H06': data[16],

                'P07': data[17],
                'H07': data[18],

                'P08': data[19],
                'H08': data[20],

                'P09': data[21],
                'H09': data[22],

                'P10': data[23],
                'H10': data[24],

                'P11': data[25],
                'H11': data[26],

                'P12': data[27],
                'H12': data[28],

                'P13': data[29],
                'H13': data[30],

                'P14': data[31],
                'H14': data[32],

                'P15': data[33],
                'H15': data[34],

                'P16': data[35],
                'H16': data[36],

                'P17': data[37],
                'H17': data[38],

                'P18': data[39],
                'H18': data[40],

                'P19': data[41],
                'H19': data[42],

                'P20': data[43],
                'H20': data[44],

                'P21': data[45],
                'H21': data[46],

                'P22': data[47],
                'H22': data[48],

                'P23': data[49],
                'H23': data[50],

                'P24': data[51],
                'H24': data[52],

                'P25': data[53],
                'H25': data[54],

                'P26': data[55],
                'H26': data[56],

                'P27': data[57],
                'H27': data[58],

                'P28': data[59],
                'H28': data[60],

                'P29': data[61],
                'H29': data[62],

                'P30': data[63],
                'H30': data[64],

                'P31': data[65],
                'H31': data[66],
                'monitor_id': self.id,
            }
            if new_lines:
                self.env['wizard.report.monitor.du'].create(new_lines)



class WizardReportMonitorDu(models.TransientModel):
    _name           = 'wizard.report.monitor.du'
    _description    = 'Laporan Monitor Daftar Upah'

    Kemandoran_id    = fields.Many2one(comodel_name="hr.foreman", string="Kemandoran", ondelete="restrict", readonly=True)
    nik              = fields.Char('no_induk', readonly=True)
    employee_id      = fields.Many2one(comodel_name="hr.employee", string="Nama", ondelete="restrict", readonly=True)
    HT               = fields.Float('HT', readonly=True)
    H01              = fields.Float('H01', readonly=True)
    H02              = fields.Float('H02', readonly=True)
    H03              = fields.Float('H03', readonly=True)
    H04              = fields.Float('H04', readonly=True)
    H05              = fields.Float('H05', readonly=True)
    H06              = fields.Float('H06', readonly=True)
    H07              = fields.Float('H07', readonly=True)
    H08              = fields.Float('H08', readonly=True)
    H09              = fields.Float('H09', readonly=True)
    H10              = fields.Float('H10', readonly=True)
    H11              = fields.Float('H11', readonly=True)
    H12              = fields.Float('H12', readonly=True)
    H13              = fields.Float('H13', readonly=True)
    H14              = fields.Float('H14', readonly=True)
    H15              = fields.Float('H15', readonly=True)
    H16              = fields.Float('H16', readonly=True)
    H17              = fields.Float('H17', readonly=True)
    H18              = fields.Float('H18', readonly=True)
    H19              = fields.Float('H19', readonly=True)
    H20              = fields.Float('H20', readonly=True)
    H21              = fields.Float('H21', readonly=True)
    H22              = fields.Float('H22', readonly=True)
    H23              = fields.Float('H23', readonly=True)
    H24              = fields.Float('H24', readonly=True)
    H25              = fields.Float('H25', readonly=True)
    H26              = fields.Float('H26', readonly=True)
    H27              = fields.Float('H27', readonly=True)
    H28              = fields.Float('H28', readonly=True)
    H29              = fields.Float('H29', readonly=True)
    H30              = fields.Float('H30', readonly=True)
    H31              = fields.Float('H31', readonly=True)
    PT               = fields.Float(digits=(16, 0), string='PT', readonly=True)
    P01              = fields.Float(digits=(16, 0), string='P01', readonly=True)
    P02              = fields.Float(digits=(16, 0), string='P02', readonly=True)
    P03              = fields.Float(digits=(16, 0), string='P03', readonly=True)
    P04              = fields.Float(digits=(16, 0), string='P04', readonly=True)
    P05              = fields.Float(digits=(16, 0), string='P05', readonly=True)
    P06              = fields.Float(digits=(16, 0), string='P06', readonly=True)
    P07              = fields.Float(digits=(16, 0), string='P07', readonly=True)
    P08              = fields.Float(digits=(16, 0), string='P08', readonly=True)
    P09              = fields.Float(digits=(16, 0), string='P09', readonly=True)
    P10              = fields.Float(digits=(16, 0), string='P10', readonly=True)
    P11              = fields.Float(digits=(16, 0), string='P11', readonly=True)
    P12              = fields.Float(digits=(16, 0), string='P12', readonly=True)
    P13              = fields.Float(digits=(16, 0), string='P13', readonly=True)
    P14              = fields.Float(digits=(16, 0), string='P14', readonly=True)
    P15              = fields.Float(digits=(16, 0), string='P15', readonly=True)
    P16              = fields.Float(digits=(16, 0), string='P16', readonly=True)
    P17              = fields.Float(digits=(16, 0), string='P17', readonly=True)
    P18              = fields.Float(digits=(16, 0), string='P18', readonly=True)
    P19              = fields.Float(digits=(16, 0), string='P19', readonly=True)
    P20              = fields.Float(digits=(16, 0), string='P20', readonly=True)
    P21              = fields.Float(digits=(16, 0), string='P21', readonly=True)
    P22              = fields.Float(digits=(16, 0), string='P22', readonly=True)
    P23              = fields.Float(digits=(16, 0), string='P23', readonly=True)
    P24              = fields.Float(digits=(16, 0), string='P24', readonly=True)
    P25              = fields.Float(digits=(16, 0), string='P25', readonly=True)
    P26              = fields.Float(digits=(16, 0), string='P26', readonly=True)
    P27              = fields.Float(digits=(16, 0), string='P27', readonly=True)
    P28              = fields.Float(digits=(16, 0), string='P28', readonly=True)
    P29              = fields.Float(digits=(16, 0), string='P29', readonly=True)
    P30              = fields.Float(digits=(16, 0), string='P30', readonly=True)
    P31              = fields.Float(digits=(16, 0), string='P31', readonly=True)

    monitor_id = fields.Many2one(comodel_name='wizard.report.monitor', string='Laporan Monitor', required=True, ondelete="cascade", copy=False)


class WizardReportMonitorDuSelect(models.TransientModel):
    _name = "wizard.report.monitor.du.select"
    _description = "Laporan Monitor DU Harian"

    name = fields.Selection([('monitor_du', 'Monitoring DU Harian'),
                             ], string='Choose Report', default='monitor_du')

    report_type = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='xls')

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name_report = False
        if self.name == "monitor_du":
            name_report = "report_monitor_du"
        else:
            return True
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name_report,
            'datas': {
                'model': 'wizard.report.monitor.du.select',
                'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type': data['report_type'],
                'form': data
            },
            'nodestroy': False
        }