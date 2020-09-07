# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

class DebitNote(models.Model):
    _name = 'account.debit.note'
    _inherit = ['mail.thread']
    _description = "Debit Note"
    _order = "date desc, id desc"

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id

    name = fields.Char(string='Debit Note Number', index=True,
        readonly=True, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on account move lines')
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this debit note.",
        readonly=True, states={'draft': [('readonly', False)]})
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]})

    state = fields.Selection([
            ('draft','Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Debit Note.\n"
             " * The 'Open' status is used when user creates debit note, an debit note number is generated. It stays in the open status till the user pays the debit note.\n"
             " * The 'Posted' status is set automatically when the debit note already had a adjustmet journal. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel debit note.")
    invoice_id = fields.Many2one('account.invoice', string='Add Invoice', required=True, copy=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    date = fields.Date(string='Date', required=True, 
        copy=False,
        help="Debit Note Date",
        readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Monetary(string='Amount', required=True, 
        readonly=True, states={'draft': [('readonly', False)]})

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this debit note.")
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain="[('type', '=', 'purchase'),('company_id', '=', company_id)]")
    move_id = fields.Many2one('account.move', string='Journal Entry',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items.")

    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.debit.note'))

    # _sql_constraints = [
    #     ('number_uniq', 'unique(number, company_id, currency_id)', 'Debit Note Number must be unique per Company!'),
    # ]

    # @api.model
    # def create(self, vals):
    #     debit_note = super(DebitNote, self).create(vals)
    #     return debit_note

    @api.multi
    def debit_note_print(self):
        """ Print the debit note and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        return self.env['report'].get_action(self, 'account.report_debit_note')

    @api.multi
    def unlink(self):
        for debit_note in self:
            if debit_note.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an debit note which is not draft or cancelled. You should refund it instead.'))
            elif debit_note.move_id:
                raise UserError(_('You cannot delete an debit note after it has been adjusted. You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(DebitNote, self).unlink()

    @api.multi
    def action_debit_note_draft(self):
        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Debit Note must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft'})
        return True

    @api.multi
    def account_move_get(self):
        if self.name:
            name = self.name
        elif self.journal_id.sequence_id:
            if not self.journal_id.sequence_id.active:
                raise UserError(_('Please activate the sequence of selected journal !'))
            name = self.journal_id.sequence_id.with_context(ir_sequence_date=self.date).next_by_id()
        else:
            raise UserError(_('Please define a sequence on the journal.'))

        move = {
            'name': name,
            'journal_id': self.journal_id.id,
            'date': self.date,
            # 'ref': self.reference,
        }
        return move

    def _prepare_credit_move_line(self, move):
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        debit = credit = 0.0
        amount = current_currency!=company_currency and \
            current_currency.with_context({'date': move.date}).compute(self.amount, company_currency) \
            or self.amount
        if amount > 0:
            credit = amount
        else:
            debit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.account_id.id,
            # 'analytic_account_id': self.analytic_account_id.id,
            'partner_id': self.partner_id.id,
            'name': move.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and -1*self.amount or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }

    def _prepare_debit_move_line(self, move):
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        debit = credit = 0.0
        amount = current_currency!=company_currency and \
            current_currency.with_context({'date': move.date}).compute(self.amount, company_currency) \
            or self.amount
        if amount > 0:
            debit = amount
        else:
            credit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.invoice_id.account_id.id,
            # 'analytic_account_id': self.analytic_account_id.id,
            'partner_id': self.partner_id.id,
            'name': move.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and -1*self.amount or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }

    @api.multi
    def action_debit_note_open(self):
        # lots of duplicate calls to action_debit_note_open, so we remove those already open
        to_open_debit_notes = self.filtered(lambda inv: inv.state != 'open')
        if to_open_debit_notes.filtered(lambda inv: inv.state!='draft'):
            raise UserError(_("Debit Note must be in draft or Pro-forma state in order to validate it."))
        
        MoveLine = self.env['account.move.line']
        for debnote in self:
            ctx = self._context.copy()
            ctx['date'] = debnote.date
            ctx['check_move_validity'] = False

            move = self.env['account.move'].create(debnote.account_move_get())

            move_line_vals = debnote._prepare_credit_move_line(move)
            MoveLine.with_context(ctx).create(move_line_vals)

            move_line_vals = debnote._prepare_debit_move_line(move)
            debit_move_line = MoveLine.with_context(ctx).create(move_line_vals)
            debnote.invoice_id.register_payment(debit_move_line)
            debnote.move_id = move.id
            debnote.name = move.name
        return self.write({'state': 'posted'})

    @api.multi
    def action_debit_note_cancel(self):
        if self.filtered(lambda dn: dn.state not in ['draft', 'posted']):
            raise UserError(_("Debit Note must be in draft or posted state in order to be cancelled."))
        for debnote in self:
            debnote.move_id.line_ids.remove_move_reconcile()
            debnote.move_id.button_cancel()
            debnote.move_id.unlink()
        return self.write({'state': 'cancel'})

    # Load Invoice
    @api.onchange('invoice_id')
    def invoice_change(self):
        if not self.invoice_id:
            return {}
        elif self.invoice_id.state!='open':
            self.invoice_id = False
            return {
                'warning': {'title': 'Onchange Error', 
                    'message': 'Invoice must be in Open state.'}
            }

        if not self.partner_id:
            self.partner_id = self.invoice_id.partner_id.id
        self.origin = self.invoice_id.reference or self.invoice_id.number
        self.currency_id = self.invoice_id.currency_id.id
        return {}

    @api.onchange('invoice_id', 'amount')
    def onchange_amount(self):
        if not self.invoice_id:
            self.amount = 0.0
        if self.amount > self.invoice_id.residual:
            self.amount = self.invoice_id.residual
            raise ValueError(_('Amount has to be greater than Invoice Amount Due.'))