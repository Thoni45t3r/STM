# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    writeoff_sale_account_asset_id = fields.Many2one('account.account', 'Write-off Sale Account')

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    prev_accumulated_depr = fields.Float(string='Prev. Accumulated Depreciation', digits=0, readonly=True, states={'draft': [('readonly', False)]},
        help="It is the acculumated depreciation amount of the Opening Asset Entry.")
    disposal_reason = fields.Text(string='Disposal Reason', readonly=True)
    disposal_method = fields.Selection(selection=[('asset_sale', 'Sold'), ('asset_dispose', 'Disposed')], string='Disposal Method', readonly=True)
    disposal_move_id = fields.Many2one('account.move', 'Disposal Entry', readonly=True)
    disposal_invoice_id = fields.Many2one('account.invoice', 'Sales Invoice Asset', readonly=True)
    disposal_move_line_ids = fields.One2many('account.move.line', related='disposal_move_id.line_ids', string='Disposal Asset', readonly=True)

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'disposal_reason': '',
            'disposal_method': False,
            'disposal_move_id': False,
            'disposal_invoice_id': False,
        })
        return super(AccountAssetAsset, self).copy(default)
    
    @api.multi
    def validate(self):
        self.write({'state': 'open'})
        fields = [
            'method',
            'method_number',
            'method_period',
            'method_end',
            'method_progress_factor',
            'method_time',
            'salvage_value',
            'prev_accumulated_depr',
            'invoice_id',
        ]
        ref_tracked_fields = self.env['account.asset.asset'].fields_get(fields)
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.method == 'linear':
                del(tracked_fields['method_progress_factor'])
            if asset.method_time != 'end':
                del(tracked_fields['method_end'])
            else:
                del(tracked_fields['method_number'])
            dummy, tracking_value_ids = asset._message_track(tracked_fields, dict.fromkeys(fields))
            asset.message_post(subject=_('Asset created'), tracking_value_ids=tracking_value_ids)

    @api.one
    @api.depends('value', 'prev_accumulated_depr', 'salvage_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount', 'disposal_move_id.state')
    def _amount_residual(self):
        total_amount = 0.0
        for line in self.depreciation_line_ids:
            if line.move_check:
                total_amount += line.amount
        if self.disposal_move_id and self.disposal_move_id.state=='posted':
            self.value_residual = 0.0
        else:
            self.value_residual = self.value - total_amount - (self.prev_accumulated_depr + self.salvage_value)

class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    disposal_method = fields.Selection([('asset_sale', 'Sold'), ('asset_dispose', 'Disposed')], string='Disposal Method')
    disposal_reason = fields.Text(string='Disposal Reason')

    @api.model
    def _cron_depreciate(self):
        to_depreciate = self.search([('depreciation_date','<=',fields.Date.context_today(self)), ('asset_id.state','=','open'), ('move_id','=',False)])
        to_depreciate.create_move(datetime.today())