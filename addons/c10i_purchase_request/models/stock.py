# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import warnings
from openerp.exceptions import except_orm, Warning, RedirectWarning

class stock_picking(models.Model):
    _inherit = 'stock.picking'



    boolean_check_expired = fields.Boolean('Check Expired', default=False)


    @api.multi
    def check_expired(self):
    	purchase_obj = self.env['purchase.order'].search([('name','=',self.origin)])
        date_expired = purchase_obj.date_end
        date_expired_formatted = datetime.strptime(date_expired, '%Y-%m-%d')
        today = fields.Date.today()
        date_now_formatted = datetime.strptime(today, '%Y-%m-%d')
        diff_date = str((date_now_formatted - date_expired_formatted).days)
        diff_date_int = int(diff_date)
        picking_in = self.env.ref('stock.picking_type_in')
        print "qqqqq", diff_date_int
        if self.picking_type_id == picking_in and diff_date_int > 0:
            #raise warnings.warn("Warning...........Message")
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'validate.po.expired',
                'view_mode': 'form',
                'view_type': 'form',
                'views': [(False, 'form')],
                'target': 'new',
             }
        else:
            self.boolean_check_expired = True
        







class validate_po_expired(models.Model):
    _name = 'validate.po.expired'


    @api.multi
    def validate(self):
        picking_id = self._context.get('active_id')
        stock_picking_id = self.env['stock.picking'].search([('id','=',picking_id)])
        #print "xxxxxxxxxxxxxxxxxxxxxx", stock_picking_id
        stock_picking_id.write({'boolean_check_expired': True})







    