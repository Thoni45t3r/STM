from odoo import models, fields, tools, api, _
from datetime import datetime
import time
import datetime


class WizardExportDataSelect(models.TransientModel):
    _name = "wizard.report.export.data.select"
    _description = "Laporan Export Select"
    
    from_date     = fields.Date("Periode Dari Tgl", required=True)
    to_date       = fields.Date("Sampai Tgl", required=True)
    report_type   = fields.Selection([('xlsx', 'XLSX'), ('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='xlsx')
    
    name          = fields.Selection([('lhm', 'Export Progres LHM'),
                                ('kontraktor', 'Export  Progres Buku Kontraktor'),
                                ('kontraktor_alat', 'Export  Progres Buku Kontraktor Alat'),
                                ('upah', 'Export Detail Upah'),
                                ('rekap_hk', 'Export Data Upah - Rekap HK'),
                                ('lhm_detail', 'Export Transaksi Detail LHM'),
                                ('karyawan', 'Export Master Data Karyawan'),
                                ('vehicle', 'Export Buku Kendaraan (VH)'),
                                ('machine', 'Export Buku Mesin (MA)'),
                                ('workshop', 'Export Buku Workshop (WS)'),
                                ], string='Choose Report', default='lhm')

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name_report = False
        if self.name == "lhm":
            name_report = "report_export_data_lhm_progres"
        elif self.name == "kontraktor":
            name_report = "report_export_data_kontraktor"
        elif self.name == "kontraktor_alat":
            name_report = "report_export_data_kontraktor_alat"
        elif self.name == "upah":
            name_report = "report_export_data_upah"
        elif self.name == "rekap_hk":
            name_report = "report_export_data_rekap_hk"
        elif self.name == "lhm_detail":
            name_report = "report_export_data_lhm_detail"
        elif self.name == "karyawan":
            name_report = "report_export_data_karyawan"
        elif self.name == "vehicle":
            name_report = "report_export_data_vehicle"
        elif self.name == "machine":
            name_report = "report_export_data_machine"
        elif self.name == "workshop":
            name_report = "report_export_data_workshop"
        else:
            return True
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name_report,
            'datas': {
                'model': 'wizard.report.export.data.select',
                'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type': data['report_type'],
                'form': data
            },
            'nodestroy': False
        }