##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################
from odoo import api, fields, models, _

class wizard_report_inventory(models.TransientModel):
    _name           = "wizard.report.inventory"
    _description    = "Laporan Inventory"

    from_date     = fields.Date("Periode Dari Tgl", required=True)
    to_date       = fields.Date("Sampai Tgl", required=True)
    report_type   = fields.Selection([('xlsx', 'XLSX'), ('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='xlsx')
    
    name          = fields.Selection([('skb_qty', 'SKB QTY'),
                                ('skb_qty_rp', 'SKB QTY-RP'),
                                ('skb_cost', 'SKB WP Cost'),
                                ('stock_qty_rp', 'STOCK QTY-RP'),
                                ('stock_qty_rp', 'STOCK QTY-RP'),
                                ], string='Choose Report', default='skb_qty')

    operating_unit_ids = fields.Many2many(comodel_name='operating.unit', string='Operating Unit', ondelete="restrict")


    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name_report = False
        if self.name == "skb_qty":
            name_report = "report_inventory_skb_qty"
        elif self.name == "skb_qty_rp":
            name_report = "report_inventory_skb_qty_rp"
        elif self.name == "skb_cost":
            name_report = "report_inventory_skb_qty_cost"
        elif self.name == "stock_qty":
            name_report = "report_inventory_stock_qty"
        elif self.name == "stock_qty_rp":
            name_report = "report_inventory_stock_qty_rp"
        else:
            return True
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name_report,
            'datas': {
                'model': 'wizard.report.inventory',
                'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type': data['report_type'],
                'form': data,
            },
            'nodestroy': False
        }
