# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class purchase_rfq(models.Model):
    _inherit        = 'purchase.rfq'
    
    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
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
    def create(self, vals):
        if vals.get('operating_unit_id',False):
            seq = self.env['ir.sequence'].with_context({'force_operating_unit': vals['operating_unit_id']})
        elif self._context.get('operating_unit_id',False):
            seq = self.env['ir.sequence'].with_context({'force_operating_unit': self._context.get('operating_unit_id')})
        else:
            seq = self.env['ir.sequence']
        vals['name'] = (vals.get('name','New')=='New' or 'name' not in vals.keys()) and seq.next_by_code('seq.purchase.rfq') or vals['name']
        return super(purchase_rfq, self).create(vals)

class purchase_rfq_line(models.Model):
    _inherit    = 'purchase.rfq.line'

    operating_unit_id   = fields.Many2one(
        'operating.unit',
        related='rfq_id.operating_unit_id',
        string='Operating Unit', readonly=True,
        store=True,
    )