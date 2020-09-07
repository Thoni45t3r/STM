##############################################################################
#                                                                            #
#   --- Joko Waluyo ---                                                      #
#                                                                            #
##############################################################################
from odoo import api, fields, models, _

class wizard_report_invoice(models.TransientModel):
    _name           = "wizard.report.invoice"
    _description    = "Report Invoice Model"

    name = fields.Selection([('invoice', 'Invoice Customer'),
                             ('kwitansi', 'Kwitansi'),
                             ], string='Choose Report', default='invoice')

    paper_size      = fields.Selection([('a4', 'A4')], string="Paper Size", default="a4")
    report_type     = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='pdf')

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        
        name_report = False
        if self.name == "invoice":
            name_report = "report_invoice_a4"
        elif self.name == "kwitansi":
            name_report = "report_invoice_kwitansi_a42"
        else:
            return True
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name_report,
            'datas'         : {
                'model'         : 'wizard.report.invoice',
                'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type'   : data['report_type'],
                'form'          : data
             },
            'nodestroy': False
        }

wizard_report_invoice()