# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import api, fields, models

class wizard_report_stock_card(models.TransientModel):
    _name = "wizard.report.stock.card"
    
    from_date   = fields.Date(required=True, default=lambda self: self._context.get('From', fields.Date.context_today(self)))
    to_date     = fields.Date(required=True, default=lambda self: self._context.get('To', fields.Date.context_today(self)))
    report_type = fields.Selection([('pdf', 'PDF'), ('xlsx', 'XLSX'), ('xls', 'XLS'), ], string='Report Type', default='xlsx')
    location_id = fields.Many2many('stock.location', 'stock_card_location', 'stock_card_id', string="Location", required=1)
    show_value  = fields.Selection([('cost', 'With Cost'), ('no', 'Just Stock Card')], default='no')
    product_id  = fields.Many2one('product.product', "Product", required=1)
    username    = fields.Char(string='User Print', default=lambda self: self.env.user.name)
    company_id  = fields.Many2one("res.company", "Company", required=1, default=lambda self: self.env.user.company_id)
        
    @api.multi
    def create_report(self):
        data        = self.read()[-1]
        report_name = 'report_stock_card_xls'
        cost        = False
        if data['report_type'] == 'pdf':
            report_name = 'report_stock_card'
        if data['show_value'] == 'cost':
            cost = True
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                    'model'         :'wizard.report.stock.card',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data,
                    'cost'          : cost,
                },
            'nodestroy'     : False
            }
wizard_report_stock_card()