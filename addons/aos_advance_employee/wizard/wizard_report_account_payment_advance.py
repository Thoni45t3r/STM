##############################################################################
#                                                                            #
#   --- Joko Waluyo ---                                                      #
#                                                                            #
##############################################################################
from odoo import api, fields, models, _

class wizard_report_account_payment_advance(models.TransientModel):
    _name           = "wizard.report.account.payment.advance"
    _description    = "Report Account Payment Advance"

    paper_size      = fields.Selection([('a42', 'Half Letter')], string="Paper Size", default="a42")
    report_type     = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='jrprint')

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        if self.paper_size == "a42":
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'report_account_payment_advance_a42',
                'datas': {
                    'model': 'wizard.report.account.payment.advance',
                    'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                    'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                    'report_type': data['report_type'],
                    'form': data
                },
                'nodestroy': False
            }

wizard_report_account_payment_advance()
