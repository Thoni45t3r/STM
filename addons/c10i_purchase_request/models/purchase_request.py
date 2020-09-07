# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Dion Martin
#   @modifier Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp

#####OVERRIDING ALL#####
_STATES = [
	('draft', 'Draft'),
	('to_approve', 'To be approved'),
	('approved', 'Approved'),
	('rejected', 'Rejected'),
	('done', 'Purchased'),
]

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]

class PurchaseRequest(models.Model):
    _name        	= 'purchase.request'
    _description	= 'Form Permintaan Barang'
    _inherit 		= ['mail.thread', 'ir.needaction_mixin']

    @api.model
    def _default_picking_type(self):
        type_obj 	= self.env['stock.picking.type']
        company_id 	= self.env.context.get('company_id') or self.env.user.company_id.id
        types 		= type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]

    @api.model
    def _company_get(self):
        company_id = self.env['res.company']._company_default_get(self._name)
        return self.env['res.company'].browse(company_id.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env['res.users'].browse(self.env.uid)

    name                = fields.Char('Request Reference', required=True, default="New Document", track_visibility='onchange')
    origin              = fields.Char('Source Document')
    date          		= fields.Date('Creation date', help="Date when the user initiated the request.", default=fields.Date.context_today, track_visibility='onchange')
    requested_by        = fields.Many2one('res.users', 'Requested by', required=True, track_visibility='onchange', default=_get_default_requested_by)
    approved_by         = fields.Many2one('res.users', 'Approved by', track_visibility='onchange')
    note         		= fields.Text('Note')
    picking_type_id 	= fields.Many2one('stock.picking.type', 'Picking Type', required=True, default=_default_picking_type)
    company_id          = fields.Many2one('res.company', 'Company', required=True, default=_company_get, track_visibility='onchange')
    line_ids            = fields.One2many('purchase.request.line', 'request_id', 'Products to Purchase', readonly=False, copy=True, track_visibility='onchange')
    product_service     = fields.Boolean('Service Product', default=False, copy=False, compute='_checked_type_product')
    product_other       = fields.Boolean('Non Service Product', default=False, copy=False, compute='_checked_type_product')
    finished            = fields.Boolean('Finished', compute="_compute_finished")
    purchase_order_id 	= fields.Many2one('purchase.order', 'Purchase')
    rfq_count 			= fields.Integer(string='RFQ', compute='_compute_count_rfq', readonly=True)
    purchase_count		= fields.Integer(string='Purchase Order', compute='_compute_count_purchase', readonly=True)
    priority 			= fields.Selection(selection=AVAILABLE_PRIORITIES, string='Prioritas', index=True, track_visibility='onchange', required=True, copy=False, default='0')
    state               = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', required=True, copy=False, default='draft')

    @api.multi
    @api.depends('line_ids.product_id')
    def _checked_type_product(self):
        for pr_line in self.line_ids:
            if pr_line.product_id.type == 'service':
                self.product_service = True
            else:
                self.product_other = True


    @api.multi
    def create_report(self):
        user    = self.env.user
        return {
                'type'          : 'ir.actions.report.xml',
                'report_name'   : 'report_purchase_request',
                'datas'         : {
                    'model'         : 'purchase.request',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                    'name'          : self.name or "---",
                    'user'          : user.partner_id.name or user.login
                    },
                'nodestroy'     : False
        }

    @api.multi
    def _compute_finished(self):
        for request_self in self:
            if request_self.state in ['approved', 'done']:
                residual    = 0
                for request in request_self.line_ids:
                    residual += request.residual
                if residual == 0:
                    request_self.finished   = True
                else:
                    request_self.finished   = False

    @api.multi
    def action_view_rfq(self):
        self.ensure_one()
        action 				= self.env.ref('c10i_purchase_request.action_purchase_rfq').read()[0]
        action['context'] 	= {'search_default_request_ids': self.id,}
        return action

    @api.multi
    def action_view_purchase(self):
        self.ensure_one()
        action 				= self.env.ref('purchase.purchase_form_action').read()[0]
        action['context'] 	= {'search_default_purchase_request_ids': self.id,}
        return action

    @api.depends('line_ids')
    def _compute_line_count(self):
        self.line_count = len(self.mapped('line_ids'))

    @api.multi
    def _compute_count_rfq(self):
        for order in self:
            rfq_obj 	= self.env['purchase.rfq'].search([('id', '!=', 0)])
            count 		= 0
            for x in rfq_obj:
                if order.id in x.request_ids.ids:
                    count += 1
            self.rfq_count = count

    @api.multi
    def _compute_count_purchase(self):
        for order in self:
            purchase_obj 	= self.env['purchase.order'].search([('id', '!=', 0)])
            count 			= 0
            for x in purchase_obj:
                if order.id in x.purchase_request_ids.ids:
                    count += 1
            self.purchase_count = count

    @api.multi
    def unlink(self):
        for purchase_request in self:
            if purchase_request.state != 'draft':
                raise ValidationError(_("Terjadi kesalahan (T.T). \n"
                                        "Purchase Request hanya bisa dihapus pada state Draft!"))
        request = super(PurchaseRequest, self).unlink()
        return request

    @api.multi
    def copy(self, default=None):
        default 	= dict(default or {})
        self.ensure_one()
        default.update({
            'state'	: 'draft',
        })
        return super(PurchaseRequest, self).copy(default)

    @api.model
    def create(self, vals):
        vals['name'] = vals['name']=='New Document' and self.env['ir.sequence'].next_by_code('seq.purchase.request') or vals['name']
        request = super(PurchaseRequest, self).create(vals)
        if vals.get('approved_by'):
            request.message_subscribe_users(user_ids=[request.approved_by.id])
        return request

    @api.multi
    def write(self, vals):
        res = super(PurchaseRequest, self).write(vals)
        for request in self:
            if vals.get('approved_by'):
                self.message_subscribe_users(user_ids=[request.approved_by.id])
        return res

    @api.multi
    def button_draft(self):
        return self.write({
                            'state'			: 'draft',
                            'approved_by'	: False,
                            })
    @api.multi
    def button_to_approve(self):
        for request in self.line_ids:
            if request.product_qty <= 0:
                raise ValidationError(_("Terjadi kesalahan (T.T). \n"
                                        "Qty Harus Lebih dari 0!"))
        if not self.line_ids.ids:
                raise ValidationError(_("Terjadi kesalahan (T.T). \n"
                                    "Isi detail product terlebih dahulu!"))
        return self.write({'state': 'to_approve'})

    @api.multi
    def button_approved(self):
        return self.write({
                            'state'			: 'approved',
                            'approved_by'	: self.env.uid,
                           })

    @api.multi
    def button_rejected(self):
        return self.write({
                            'state'			: 'rejected',
                            'approved_by'	: False,
                           })

    @api.multi
    def button_done(self):
        return self.write({'state': 'done'})


class PurchaseRequestLine(models.Model):
    _name 			= "purchase.request.line"
    _description 	= "Purchase Request Line"

    product_id 				= fields.Many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)])
    name 					= fields.Char('Description')
    product_uom_id 			= fields.Many2one('product.uom', 'UoM')
    product_qty 			= fields.Float('Qty', digits=dp.get_precision('Product Unit of Measure'))
    request_id 				= fields.Many2one('purchase.request', 'Purchase Request', ondelete='cascade', readonly=True)
    company_id 				= fields.Many2one('res.company', related='request_id.company_id', string='Company', store=True, readonly=True)
    date 					= fields.Date(related='request_id.date', store=True, readonly=True)
    specifications 			= fields.Text(string='Specifications')
    note 			        = fields.Text(string='Note')
    scheduled_date 			= fields.Date('Scheduled Date')
    last_purchase_price		= fields.Float('Last Price', related='product_id.product_tmpl_id.last_purchase_price')
    residual 				= fields.Float('Residual', compute='_compute_residual', readonly=True)
    state				 	= fields.Selection(selection=_STATES, string='Status', related="request_id.state", index=True, required=True, copy=False, readonly=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = '[%s] %s' % (self.product_id.code, name)
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty 	= 0.0
            self.name 			= name

    @api.multi
    def _compute_residual(self):
        for order in self:
            purchase_line   = self.env['purchase.order.line'].search([('id', '!=', 0), ('request_line_id', '=', order.id)])
            residual        = order.product_qty
            for line in purchase_line:
                if line.state in ['purchase', 'done'] and line.product_id.id == order.product_id.id:
                    residual -= line.product_qty
            order.residual = residual