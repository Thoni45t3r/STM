# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from lxml import etree

from odoo import api, fields, models, _
from odoo.osv.orm import setup_modifiers
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class AssetAddition(models.TransientModel):
    _name = "wizard.asset.addition"
    _description = 'Asset Addition'

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.user.company_id.id)
    picking_id = fields.Many2one('stock.picking', 'Receipt')
    line_ids = fields.One2many('asset.addition.line', 'wizard_id', 'Asset To be Created')

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            move_lines = []
            for move in self.picking_id.move_lines:
                if move.product_id and (not move.product_id.categ_id.asset_category \
                        or not move.product_id.categ_id.asset_category_id):
                    continue
                temp = {
                    'move_id': move.id,
                    'name': '%s: %s'%(self.picking_id.name, move.product_id.name),
                    'value': move.get_price_unit(),
                    'asset_category_id': move.product_id.categ_id.asset_category_id.id,
                }
                move_lines.append(temp)
            self.line_ids = move_lines
        else:
            self.line_ids = []

    @api.multi
    def asset_create(self):
        Asset = self.env['account.asset.asset']
        # self.ensure_one()
        asset_ids = []
        for line in self.line_ids:
            if line.move_id:
                check_asset = Asset.search([('move_id','=',line.move_id.id)])
                if check_asset:
                    raise UserError(_('This Move has already had an Asset. \nPlease remove it and then continue. \nHint: %s')%line.move_id.name)
            
            vals = {
                'name': line.name,
                'code': line.move_id and line.move_id.picking_id.name or False,
                'category_id': line.asset_category_id.id,
                'value': line.value,
                'partner_id': line.move_id.picking_id and line.move_id.picking_id and line.move_id.picking_id.partner_id and line.move_id.picking_id.partner_id.id or False,
                'company_id': self.env.user.company_id.id,
                'currency_id': self.env.user.company_id.currency_id.id,
                'date': line.move_id and line.move_id.date or datetime.today(),
                'move_id': line.move_id.id,
            }
            changed_vals = Asset.onchange_category_id_values(vals['category_id'])
            vals.update(changed_vals['value'])
            asset = Asset.create(vals)
            asset_ids.append(asset.id)
            if line.asset_category_id.open_asset:
                asset.validate()
        
        if asset_ids:
            name = _('Asset')
            view_mode = 'form'
            if len(asset_ids) > 1:
                name = _('Assets')
                view_mode = 'tree,form'
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': view_mode,
                'res_model': 'account.asset.asset',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': asset_ids[0],
            }

class AssetAdditionLine(models.TransientModel):
    _name = "asset.addition.line"

    wizard_id = fields.Many2one('wizard.asset.addition', 'Wizard')
    move_id = fields.Many2one('stock.move', 'Move ID')
    asset_category_id = fields.Many2one('account.asset.category', 'Asset Category', required=True)
    name = fields.Char('Asset Description', required=True)
    value = fields.Float(string='Asset Value', required=True, digits=0)