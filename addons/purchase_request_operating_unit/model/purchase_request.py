# -*- coding: utf-8 -*-
# Copyright 2016-17 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# Copyright 2016-17 Serpent Consulting Services Pvt. Ltd.
#   (<http://www.serpentcs.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        default=lambda self:
        self.env['res.users'].
        operating_unit_default_get(self._uid),
    )

    @api.multi
    @api.constrains('operating_unit_id', 'company_id')
    def _check_company_operating_unit(self):
        for rec in self:
            if rec.company_id and rec.operating_unit_id and \
                    rec.company_id != rec.operating_unit_id.company_id:
                raise ValidationError(_('The Company in the Purchase Request '
                                        'and in the Operating Unit must be'
                                        'the same.'))

    @api.multi
    @api.constrains('operating_unit_id', 'picking_type_id')
    def _check_warehouse_operating_unit(self):
        for rec in self:
            picking_type = rec.picking_type_id
            if picking_type:
                if picking_type.warehouse_id and\
                        picking_type.warehouse_id.operating_unit_id\
                        and rec.operating_unit_id and\
                        picking_type.warehouse_id.operating_unit_id !=\
                        rec.operating_unit_id:
                    raise ValidationError(_('Configuration error!\nThe\
                    Purchase Request and the Warehouse of picking type\
                    must belong to the same Operating Unit.'))

    @api.model
    def _default_picking_type(self):
        type_obj            = self.env['stock.picking.type']
        company_id          = self.env.context.get('company_id') or self.env.user.company_id.id
        operating_unit_id   = self._context.get('operating_unit_id', self.env['res.users'].operating_unit_default_get(self._uid))
        types               = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id),('warehouse_id.operating_unit_id','=',operating_unit_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]

    @api.onchange('operating_unit_id')
    def _onchange_operating_unit(self):
        self.picking_type_id = self.with_context({'operating_unit_id': self.operating_unit_id.id})._default_picking_type()

    @api.model
    def create(self, vals):
        if vals.get('operating_unit_id', False):
            seq = self.env['ir.sequence'].with_context({'force_operating_unit':vals['operating_unit_id']})
        else:
            seq = self.env['ir.sequence']
        vals['name'] = (vals.get('name','New Document')=='New Document' or  'name' not in vals.keys()) and self.env['ir.sequence'].with_context({'force_operating_unit':vals['operating_unit_id']}).next_by_code('seq.purchase.request') or vals['name']
        request = super(PurchaseRequest, self).create(vals)
        if vals.get('approved_by'):
            request.message_subscribe_users(user_ids=[request.approved_by.id])
        return request


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    operating_unit_id = fields.Many2one(
        'operating.unit',
        related='request_id.operating_unit_id',
        string='Operating Unit', readonly=True,
        store=True,
    )
