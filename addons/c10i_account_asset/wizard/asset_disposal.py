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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

class AssetDisposal(models.TransientModel):
    _name = 'wizard.asset.disposal'
    _description = 'Disposing Asset'

    dispose_method = fields.Selection([('asset_sale', 'To be Sale'), ('asset_dispose', 'To be Dispose')], string='Disposal Method', required=True, default='asset_dispose',
        help="Choose the Action to be use for disposing asset.\n"
            "  * To be Sale: Create a Customer Invoice for Selling asset to a Customer\n"
            "  * To be Dispose: Create a Journal Entry")
    create_invoice = fields.Boolean(string='Create Invoice', help="It will two documents, the first is Customer Invoice \n"
        "and the second is Reclass Depreciation Asset Entry")
    partner_id = fields.Many2one('res.partner', 'Customer')
    sale_account_asset_id = fields.Many2one('account.account', 'Sales Account')
    date_invoice = fields.Date('Invoice Date')
    name = fields.Text(string='Disposal Reason', required=True)
    gross_value = fields.Float(string='Gross Value', digits=0, readonly=True,
        help="This is the gross amount when you purchase the Asset.")
    current_cumm_depr_amount = fields.Float(string='Current Cummulative Depr. Amount', digits=0, readonly=True,
        help="All cummulative depreciation amount before we dispose/sell the asset.")
    cumm_depr_amount = fields.Float(compute='_compute_writeoff', string='Cummulative Depr. Amount', digits=0,
        help="All cummulative depreciation amount before we dispose/sell the asset.")
    sale_amount = fields.Float(string='Sale Amount', digits=0,
        help="It is the amount you plan to sell this asset.")
    write_off_amount = fields.Float(compute='_compute_writeoff', string='Write Off Amount')
    with_depr = fields.Boolean(string='Create Last Depreciation before Sales', help="It will create a depreciation Entry \n"
        "from the Last Depreciation until previous day before Selling Asset")
    extra_depr_amount = fields.Float(compute='_compute_writeoff', string='Depr. Amount', digits=0,
        help="This is the additional depreciation that you'll make before dispose/sell your Asset.")

    @api.model
    def default_get(self, default_fields):
        AssetObj = self.env['account.asset.asset']
        context = self._context
        
        data = super(AssetDisposal, self).default_get(default_fields)
        if context.get('active_id'):
            asset = AssetObj.browse(context['active_id'])
            data['gross_value'] = asset.value
            data['current_cumm_depr_amount'] = asset.value - asset.salvage_value - asset.value_residual
        return data

    @api.depends('sale_amount', 'gross_value', 'current_cumm_depr_amount', 'with_depr', 'date_invoice')
    def _compute_writeoff(self):
        AssetObj = self.env['account.asset.asset']
        if self.with_depr and self.date_invoice:
            asset = AssetObj.browse(self.env.context.get('active_id', False))
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check).sorted(key=lambda l: l.depreciation_date)
            posted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
            residual_amount = asset.value_residual
            # Firstly, we will looking for the prev depreciation that should be post 
            # but hasn't been posted yet. it is used for either prorata or non prorata asset
            temp1 = asset.depreciation_line_ids.filtered(lambda x: not x.move_check and x.depreciation_date<self.date_invoice)
            extra_depr = 0.0
            if temp1:
                for depr in temp1:
                    residual_amount -= depr.amount
                    extra_depr += depr.amount
                unposted_depreciation_line_ids = unposted_depreciation_line_ids.filtered(lambda x: x.id not in [y.id for y in temp1]).sorted(key=lambda l: l.depreciation_date)
            
            last_posted_depr = temp1 and temp1[-1] or (posted_depreciation_line_ids and posted_depreciation_line_ids[-1] or False)
            last_posted_depr_date = last_posted_depr and datetime.strptime(last_posted_depr.depreciation_date, DF) or datetime.strptime(asset.date, DF)
            if not asset.prorata and unposted_depreciation_line_ids:
                last_unposted_depr = unposted_depreciation_line_ids[0]
                unposted_depreciation_line_ids = unposted_depreciation_line_ids.filtered(lambda x: x.id!=last_unposted_depr.id).sorted(key=lambda l: l.depreciation_date)
                
                current_depr_date = datetime.strptime(last_unposted_depr.depreciation_date, DF)
                total_days = (current_depr_date - last_posted_depr_date).days
                depr_days = (datetime.strptime(self.date_invoice, DF) - last_posted_depr_date).days
                
                last_day_amount = last_unposted_depr.amount / total_days * depr_days
                residual_amount -= last_day_amount
                extra_depr += last_day_amount
            self.extra_depr_amount = extra_depr
            self.cumm_depr_amount = asset.value - asset.salvage_value - residual_amount
            self.write_off_amount = self.gross_value - self.sale_amount - (asset.value - asset.salvage_value - residual_amount)
        else:
            self.cumm_depr_amount = self.current_cumm_depr_amount
            self.extra_depr_amount = 0
            self.write_off_amount = self.gross_value - self.sale_amount - self.current_cumm_depr_amount

    @api.multi
    def dispose(self):
        asset_id = self.env.context.get('active_id', False)
        AssetObj = self.env['account.asset.asset']
        asset = AssetObj.browse(asset_id)
        self.ensure_one()
        if self.dispose_method == 'asset_sale':
            asset_to_update = {}
            invoice = False
            # BEGIN: Post and Create Last Depreciation
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check).sorted(key=lambda l: l.depreciation_date)
            posted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
            residual_amount = asset.value_residual
            commands = []
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                    'disposal_invoice_id': False,
                }

                # Create a last remaining days of the last depreciatoin period before Selling and post it
                if self.with_depr:
                    # Firstly, we will looking for the prev depreciation that should be post 
                    # but hasn't been posted yet. it is used for either prorata or non prorata asset
                    temp1 = asset.depreciation_line_ids.filtered(lambda x: not x.move_check and x.depreciation_date<self.date_invoice)
                    if temp1:
                        for depr in temp1:
                            residual_amount -= depr.amount
                            depr.create_move(post_move=False)
                        unposted_depreciation_line_ids = unposted_depreciation_line_ids.filtered(lambda x: x.id not in [y.id for y in temp1]).sorted(key=lambda l: l.depreciation_date)
                    
                    last_posted_depr = temp1 and temp1[-1] or (posted_depreciation_line_ids and posted_depreciation_line_ids[-1] or False)
                    last_posted_depr_date = last_posted_depr and datetime.strptime(last_posted_depr.depreciation_date, DF) or datetime.strptime(asset.date, DF)
                    if not asset.prorata:
                        last_unposted_depr = unposted_depreciation_line_ids[0]
                        unposted_depreciation_line_ids = unposted_depreciation_line_ids.filtered(lambda x: x.id!=last_unposted_depr.id).sorted(key=lambda l: l.depreciation_date)
                        
                        current_depr_date = datetime.strptime(last_unposted_depr.depreciation_date, DF)
                        total_days = (current_depr_date - last_posted_depr_date).days
                        depr_days = (datetime.strptime(self.date_invoice, DF) - last_posted_depr_date).days
                        
                        last_day_amount = last_unposted_depr.amount / total_days * depr_days
                        residual_amount -= last_day_amount
                        last_unposted_depr.write({'amount': last_day_amount, 
                            'depreciated_value': last_posted_depr.depreciated_value + last_day_amount, 
                            'depreciation_date': self.date_invoice, 
                            'remaining_value': residual_amount})
                        last_unposted_depr.create_move(post_move=False)
                
                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

            # Create a new depr. line with the residual amount
            sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids)
            # vals = {
            #     'amount': residual_amount,
            #     'asset_id': asset.id,
            #     'sequence': sequence,
            #     'name': (asset.code or '') + '/' + str(sequence),
            #     'remaining_value': 0,
            #     'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
            #     'depreciation_date': self.date_invoice,
            #     'disposal_method': self.dispose_method,
            #     'disposal_reason': self.name,
            # }
            # END: Post and Create Last Depreciation
            # BEGIN: Create Reclass Entry
            # created_moves = self.env['account.move']
            prec = self.env['decimal.precision'].precision_get('Account')
            if asset.disposal_move_id:
                raise UserError(_('This depreciation is already linked to a journal entry! Please post or delete it.'))
            category_id = asset.category_id
            disposal_date = self.date_invoice
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            gross_value = current_currency.with_context(date=disposal_date).compute(self.gross_value, company_currency)
            cumm_depr_amount = current_currency.with_context(date=disposal_date).compute(self.cumm_depr_amount, company_currency)
            sale_amount = current_currency.with_context(date=disposal_date).compute(self.sale_amount, company_currency)
            # Firstly, put all gross Value in credit to nullify asset value
            move_lines = []
            move_line_1 = {
                'name': 'Sale Asset: %s'%asset.name,
                'account_id': category_id.account_asset_id.id,
                'debit': 0.0 if float_compare(gross_value, 0.0, precision_digits=prec) > 0 else -gross_value,
                'credit': gross_value if float_compare(gross_value, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': category_id.journal_id.id,
                'partner_id': asset.partner_id.id,
                'analytic_account_id': False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * self.gross_value or 0.0,
            }
            move_lines.append((0, 0, move_line_1))
            # And then, put all cummulative Depreciation Value in debit to nullify all previous Depreciatoin
            move_line_2 = {
                'name': 'Sale Asset: %s'%asset.name,
                'account_id': category_id.account_depreciation_id.id,
                'credit': 0.0 if float_compare(cumm_depr_amount, 0.0, precision_digits=prec) > 0 else -cumm_depr_amount,
                'debit': cumm_depr_amount if float_compare(cumm_depr_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': category_id.journal_id.id,
                'partner_id': asset.partner_id.id,
                'analytic_account_id': False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and self.cumm_depr_amount or 0.0,
            }
            move_lines.append((0, 0, move_line_2))
            # Lastlym create the AR or Sales Moves
            if self.create_invoice:
                account3 = self.sale_account_asset_id.id
            else:
                account3 = self.partner_id.property_account_receivable_id.id,
            move_line_3 = {
                'name': 'Sale Asset: %s'%asset.name,
                'account_id': account3,
                'credit': 0.0 if float_compare(sale_amount, 0.0, precision_digits=prec) > 0 else -sale_amount,
                'debit': sale_amount if float_compare(sale_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': category_id.journal_id.id,
                'partner_id': self.partner_id.id,
                'analytic_account_id': False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and self.sale_amount or 0.0,
            }
            move_lines.append((0, 0, move_line_3))
            if self.write_off_amount:
                write_off_amount = current_currency.with_context(date=disposal_date).compute(self.write_off_amount, company_currency)
                account_id = category_id.writeoff_sale_account_asset_id
                if not account_id:
                    raise UserError(_('Please define Writeoff Account inside your Asset Type.'))
                move_line_4 = {
                    'name': write_off_amount<0 and 'Laba Penjualan Asset: %s'%asset.name or 'Rugi Penjualan Asset: %s'%asset.name,
                    'account_id': account_id.id,
                    'debit': write_off_amount if float_compare(write_off_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                    'credit': 0.0 if float_compare(write_off_amount, 0.0, precision_digits=prec) > 0 else -write_off_amount,
                    'journal_id': category_id.journal_id.id,
                    'partner_id': self.partner_id.id,
                    'analytic_account_id': False,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and self.write_off_amount or 0.0,
                }
                move_lines.append((0, 0, move_line_4))
            move_vals = {
                'ref': asset.code,
                'date': disposal_date or False,
                'journal_id': category_id.journal_id.id,
                'line_ids': move_lines,
            }
            move = self.env['account.move'].create(move_vals)
            asset_to_update.update({'disposal_move_id': move.id, 'depreciation_line_ids': commands, 'method_end': self.date_invoice, 
                    'method_number': sequence, 'disposal_method': self.dispose_method, 'disposal_reason': self.name})
            # created_moves |= move
            # if post_move and created_moves:
            #     created_moves.filtered(lambda m: any(m.asset_depreciation_ids.mapped('asset_id.category_id.open_asset'))).post()
            
            # End: Create Reclass Entry
            # BEGIN: Create Invoice
            if self.create_invoice:
                invoice = self.env['account.invoice'].create({
                            'name': '',
                            'type': 'out_invoice',
                            'date_invoice': self.date_invoice,
                            'account_id': self.partner_id.property_account_receivable_id.id,
                            'partner_id': self.partner_id.id,
                            'journal_id': self.env['account.invoice'].default_get(['journal_id'])['journal_id'],
                            'currency_id': asset.company_id.currency_id.id,
                            'company_id': self.env.user.company_id.id,
                        })
                if invoice:
                    invoice_line_vals = {
                        'invoice_id': invoice.id,
                        'name': asset.name,
                        'product_id': False,
                        'price_unit': self.sale_amount,
                        'uom_id': False,
                        'quantity': 1,
                        'account_id': self.sale_account_asset_id.id,
                    }
                    invoice_line_id = self.env['account.invoice.line'].create(invoice_line_vals)
                    # vals.update({'invoice_line_id': invoice_line_id})
                # commands.append((0, False, vals))
                asset_to_update.update({'disposal_invoice_id': invoice.id})
            asset_to_update.update({'state': 'close'})
            asset.write(asset_to_update)
            # Post Log Message
            tracked_fields = AssetObj.fields_get(['method_number', 'method_end', 'disposal_invoice_id'])
            changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
            if changes:
                asset.message_post(subject=_('Asset sold. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
            
            if invoice:
                name = _('Customer Invoice')
                view_mode = 'form'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': view_mode,
                    'res_model': 'account.invoice',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': invoice.id,
                }
            elif move:
                name = _('Sales Entry')
                view_mode = 'form'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': view_mode,
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': move.id,
                }
        else:
            move_ids = []
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids)
                today = datetime.today().strftime(DF)
                vals = {
                    'amount': asset.value_residual,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                    'depreciation_date': today,
                    'disposal_method': self.dispose_method,
                    'disposal_reason': self.name,
                }
                commands.append((0, False, vals))
                asset.write({'depreciation_line_ids': commands, 'method_end': today, 'method_number': sequence, 
                    'disposal_method': self.dispose_method, 'disposal_reason': self.name})
                tracked_fields = AssetObj.fields_get(['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(subject=_('Asset disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move(post_move=False)

                asset.write({
                    'disposal_method': self.dispose_method,
                    'disposal_reason': self.name,
                    'disposal_move_id': move_ids[0],
                })
            if move_ids:
                name = _('Disposal Move')
                view_mode = 'form'
                if len(move_ids) > 1:
                    name = _('Disposal Moves')
                    view_mode = 'tree,form'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': view_mode,
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': move_ids[0],
                }
