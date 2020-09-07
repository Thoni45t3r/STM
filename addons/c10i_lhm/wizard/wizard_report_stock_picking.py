##############################################################################
#                                                                            #
#   --- Joko Waluyo ---                                                      #
#                                                                            #
##############################################################################
from odoo import api, fields, models, _

class wizard_report_stock_picking(models.TransientModel):
    _name           = "wizard.report.stock.picking"
    _description    = "Report Stock Picking Model"

    paper_size      = fields.Selection([('a4', 'A4')], string="Paper Size", default="a4")
    report_type     = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='pdf')

    @api.multi
    def create_report(self):
        data = self.read()[-1]
        if self.paper_size == "a4":
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'report_stock_picking_a4',
                'datas': {
                    'model': 'wizard.report.stock.picking',
                    'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                    'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                    'report_type': data['report_type'],
                    'form': data
                },
                'nodestroy': False
            }

wizard_report_stock_picking()
