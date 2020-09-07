##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################
from odoo import api, fields, models, _

class wizard_report_cash_bank(models.TransientModel):
    _name           = "wizard.report.cash.bank"
    _description    = "Laporan cash_bank"

    from_date     = fields.Date("Periode Dari Tgl", required=True)
    to_date       = fields.Date("Sampai Tgl", required=True)
    report_type   = fields.Selection([('xlsx', 'XLSX'), ('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='xlsx')
    
    name          = fields.Selection([('cash_bank', 'Laporan Cash Bank'),
                                ('invoice', 'Daftar Invoice'),
                                ], string='Choose Report', default='cash_bank')
    
    journal_id    = fields.Many2one(comodel_name="account.journal", string="Journal Name", ondelete="restrict")

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name_report = False
        if self.name == "cash_bank":
            name_report = "report_cash_bank_cash_c10i"
        elif self.name == "invoice":
            name_report = "report_cash_bank_invoice"
        else:
            return True
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name_report,
            'datas': {
                'model': 'wizard.report.cash.bank',
                'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type': data['report_type'],
                'form': data
            },
            'nodestroy': False
        }
