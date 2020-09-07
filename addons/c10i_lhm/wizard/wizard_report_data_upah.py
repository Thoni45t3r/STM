from odoo import models, fields, tools, api, _
from datetime import datetime
import time
import datetime

################################################### Start Of Wizard Plantation Salary Select ####################################################

class WizardPlantationSalarySelect(models.TransientModel):
    _name           = "wizard.plantation.salary.select"
    _description    = "Plantation Salary Select"

    name            = fields.Selection([('daftar_upah', 'Daftar Upah'),
                                        ('slip_upah', 'Slip Gaji'),
                                        ('tanda_terima_upah', 'Tanda Terima Gaji'), ],
                                       string='Nama Laporan', default='daftar_upah')

    report_type     = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type', default='pdf')

    @api.multi
    def create_report(self):
        data        = self.read()[-1]
        name_report = False
        if self.name == "daftar_upah":
            name_report = "report_daftar_upah"
        elif self.name == "slip_upah":
            name_report = "report_slip_upah"
        elif self.name == "tanda_terima_upah":
            name_report = "report_tanda_terima_upah"
        else:
            return True
        return {
                'type'          : 'ir.actions.report.xml',
                'report_name'   : name_report,
                'datas'         : {
                    'model'         : 'wizard.plantation.salary.select',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                    'report_type'   : data['report_type'],
                    'form'          : data
                },
                'nodestroy': False
            }
################################################### End Of Wizard Plantation Salary Select ####################################################
