# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp

class account_payment(models.Model):
    _inherit = "account.payment"
    
    @api.one
    @api.depends('settlement_ids.amount_to_pay', 'currency_id', 'company_id', 'state', 'advance_type')
    def _compute_amount(self):
        self.advance_total = self.amount#sum(line.amount_to_pay for line in self.register_ids)
        self.settled_total = sum(line.amount_to_pay for line in self.settlement_ids)
        self.residual_total = self.advance_total - self.settled_total
        if self.advance_type == 'advance_emp' and self.state in ('advance','settled'):
            self.amount_charges = self.residual_total
    
    @api.one
    @api.depends('payment_type', 'amount', 'amount_charges', 'other_lines')
    def _compute_price(self):
        total_other = 0.0
        for oth in self.other_lines:
            total_other += oth.amount
        if self.advance_type == 'cash':
            self.amount_subtotal = self.amount - self.amount_charges - total_other
        else:
            self.amount_subtotal = self.amount + self.amount_charges + total_other
    
            
    state = fields.Selection(selection_add=[('advance', 'Advance'),('settled','Settled')])
    due_date = fields.Date(string='Due Date', required=False, copy=False)
    settlement_date = fields.Date(string='Settled Date', required=False, copy=False)
    advance_ids = fields.One2many('account.cadvance.line', 'payment_id', copy=False, string='Advance Lines')
    settlement_ids = fields.One2many('account.settlement.line', 'payment_id', copy=False, string='Settlement Lines')
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Advance Line')
    statement_line_id2 = fields.Many2one('account.bank.statement.line', string='Statement Settlement Line')
    advance_total = fields.Monetary(string='Advance Total',
        store=True, readonly=True, compute='_compute_amount')
    settled_total = fields.Monetary(string='Settlement Total',
        store=True, readonly=True, compute='_compute_amount')
    residual_total = fields.Monetary(string='Residual',
        store=True, readonly=True, compute='_compute_amount')
    advance_comment = fields.Text('Advance Description')
    settled_comment = fields.Text()
    amount_subtotal = fields.Monetary(string='Amount Total',
        store=True, readonly=True, compute='_compute_price')
    advance_reconciled = fields.Boolean('Advance Reconciled')

    @api.multi
    def unreconcile(self):
        """ Set back the payments in 'posted' or 'sent' state, without deleting the journal entries.
            Called when cancelling a bank statement line linked to a pre-registered payment.
        """
        for payment in self:
            if payment.advance_ids:
                if payment.state == 'reconciled':
                    payment.state = 'settled'
                else:
                    payment.advance_reconciled = False
            else:
                if payment.payment_reference:
                    payment.write({'state': 'sent'})
                else:
                    payment.write({'state': 'posted'})
    
    @api.multi
    def cancel_advance(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
            if rec.statement_line_id and rec.statement_line_id.statement_id.state == 'confirm':
                raise UserError(_("Please set the bank statement to New before canceling."))
            if rec.statement_line_id2 and rec.statement_line_id2.statement_id.state == 'confirm':
                raise UserError(_("Please set the bank statement to New before canceling."))
            if rec.statement_line_id:
                rec.statement_line_id.unlink()
            if rec.statement_line_id2:
                rec.statement_line_id2.unlink()
            for settle in rec.settlement_ids:
                settle.unlink()
            rec.state = 'draft'
            
    @api.multi
    def _create_settlement_from_entry(self):
        settle_ids = []
        for rec in self.advance_ids:
            vals = {
                'name': rec.name,
                'payment_id': self.id,
                'amount_to_pay': rec.amount_to_pay,
            }
            settle_ids.append(vals)
        return settle_ids
            
    def _create_transfer_from_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        #=======================================================================
        # CREATE JURNAL TRANSFER TO CROSS ACCOUNT
        #=======================================================================
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, self.currency_id)
        move = self.env['account.move'].create(self._get_move_transfer_vals())
        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        #print "==self.advance_type==",self._get_counterpart_register_vals(self.register_ids)
        if self.advance_type == 'advance_emp':
            counterpart_aml_dict.update(self._get_counterpart_register_vals(self.register_ids))
        else:
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        #Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)
        #=======================================================================
        # CREATE JURNAL CHARGE
        #=======================================================================
        if self.charge_account_id and self.amount_charges:
            amount_charges = self.amount_charges
            charge_debit, charge_credit, charge_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate).compute_amount_fields(-amount_charges, self.currency_id, self.company_id.currency_id, self.currency_id)
            #Write line corresponding to expense charge
            charge_counterpart_aml_dict = self._get_shared_move_line_vals(charge_debit, charge_credit, charge_amount_currency, move.id, False)
            charge_counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            charge_counterpart_aml_dict.update({'account_id': self.charge_account_id.id, 'currency_id': currency_id})
            charge_counterpart_aml = aml_obj.create(charge_counterpart_aml_dict)
            #print "====charge_counterpart_aml_dict===",charge_counterpart_aml_dict
            #Write counterpart lines with cash/bank account
            if not self.currency_id != self.company_id.currency_id:
                charge_amount_currency = 0
            charge_liquidity_aml_dict = self._get_shared_move_line_vals(charge_credit, charge_debit, -charge_amount_currency, move.id, False)
            charge_liquidity_aml_dict.update(self._get_liquidity_move_line_vals(amount_charges))
            aml_obj.create(charge_liquidity_aml_dict)
            #print "====charge_liquidity_aml_dict===",charge_liquidity_aml_dict
        #=======================================================================
        # POST MOVE
        #=======================================================================
        move.post()
        return move
    
    def _prepare_advance_statement_line_entry(self, statement):
        values = {
            'statement_id': statement.id,
            'payment_id': self.id,
            'date': self.register_date,
            'name': self.name, 
            'partner_id': self.partner_id.id,
            'ref': self.communication or '/',
            'amount': -self.amount,
        }
        return values
    
    @api.multi
    def post_advance(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #CHANGE STATE CONFIRM WHICH CAN BE POSTED
            if rec.state != 'confirm':
                raise UserError(_("Only a confirm transfer can be posted. Trying to post a payment in state %s.") % rec.state)

            # Use the right sequence to set the name
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.register_date).next_by_code('account.payment.advance.emp')

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_transfer_from_entry(amount)
            #===================================================================
            # CREATE STATEMENT
            #===================================================================
            Statement = self.env['account.bank.statement']
            StatementLine = self.env['account.bank.statement.line']
            statement_id = Statement.search([('journal_id','=',rec.journal_id.id),
                                             ('date','>=',rec.register_date),
                                             ('date','<=',rec.register_date)], limit=1)
            if not statement_id:
                statement_id = Statement.with_context({'journal_id': rec.journal_id.id}).create({'journal_id': rec.journal_id.id, 'date': rec.register_date})
            if statement_id:
                statement_line_id = StatementLine.create(rec._prepare_advance_statement_line_entry(statement_id))
                rec.write({'statement_line_id': statement_line_id.id})
            #========================IF YOU WANT DETAIL ADVANCE=================
            if rec.advance_ids:
                settled_obj = self.env['account.settlement.line']   
                settle_lines = rec._create_settlement_from_entry()
                for sline in settle_lines:
                    settled_obj.create(sline)
            #===================================================================

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.

            rec.write({'state': 'advance', 'move_name': move.name})
    
    def _create_settlement_entry(self, amount):
        """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconciliable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        
        journal = (self.residual_total <> 0.0) and self.journal_id or self.destination_journal_id
        dst_move = self.env['account.move'].create(self._get_settle_vals(journal))
        #===============================================================================
        # JURNAL EXPENSE DETAIL
        #===============================================================================
        if self.settlement_ids:
            for settle in self.settlement_ids:
                exp_debit, exp_credit, exp_amount_currency, dummy = aml_obj.with_context(date=self.settlement_date, force_rate=self.force_rate).compute_amount_fields(settle.amount_to_pay, self.currency_id, self.company_id.currency_id)
                exp_amount_currency = self.destination_journal_id.currency_id and self.currency_id.with_context(date=self.settlement_date).compute(settle.amount_to_pay, self.destination_journal_id.currency_id) or 0
        
                dst_expense_aml_dict = self._get_shared_move_line_vals(exp_debit, exp_credit, exp_amount_currency, dst_move.id)
                dst_expense_aml_dict.update({
                    'name': _('SETTLED:%s') % settle.name,
                    'account_id': settle.account_id.id,#EXPENSE ACCOUNT
                    # 'currency_id': self.destination_journal_id.currency_id.id,
                    'currency_id': self.journal_id.id,
                    'payment_id': self.id,
                    'journal_id': (self.residual_total <> 0.0) and self.journal_id.id or self.destination_journal_id.id})
                aml_obj.create(dst_expense_aml_dict)
    
        # GET BALANCE BETWEEN ADVANCE AMOUNT AND SETTLEMENT AMOUNT; 
        if self.residual_total <> 0.0:
            #print '# IF ADV > SETTLE = DEBIT; ELIF ADV < SETTLE = CREDIT'
            bal_debit, bal_credit, bal_amount_currency, dummy = aml_obj.with_context(date=self.settlement_date, force_rate=self.force_rate).compute_amount_fields(self.residual_total, self.currency_id, self.company_id.currency_id)
            counterpart_aml_residual_dict = {
                'name': 'BAL:%s' % self.name,
                'partner_id': self.payment_type in ('inbound', 'outbound') or self.advance_type == 'advance_emp'  and self.env['res.partner']._find_accounting_partner(self.partner_id).id  or False,
                'move_id': dst_move.id,
                'debit': bal_debit,
                'credit': bal_credit,
                'amount_currency': bal_amount_currency or False,
                'account_id': self.residual_account_id.id,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
                'payment_id': self.id,
            }
            counterpart_aml_residual_dict.update({'currency_id': self.currency_id.id})
            counterpart_residual_aml = aml_obj.create(counterpart_aml_residual_dict)
        #=======================================================================
        # JURNAL ADVANCE [MUST BE SAME TO RECONCILE] CREATE JUST 1 MOVE LINE
        #=======================================================================
        adv_debit, adv_credit, adv_amount_currency, dummy = aml_obj.with_context(date=self.settlement_date, force_rate=self.force_rate).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        adv_amount_currency = self.destination_journal_id.currency_id and self.currency_id.with_context(date=self.settlement_date).compute(amount, self.destination_journal_id.currency_id) or 0

        advance_debit_aml_dict = self._get_shared_move_line_vals(adv_credit, adv_debit, 0, dst_move.id)
        advance_debit_aml_dict.update({
            'name': self.name,
            'payment_id': self.id,
            'account_id': self.destination_account_id.id,
            # 'journal_id': self.destination_journal_id.id
            'journal_id': self.journal_id.id,
            })
        if self.currency_id != self.company_id.currency_id:
            advance_debit_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
            })
        advance_debit_aml = aml_obj.create(advance_debit_aml_dict)
        
        dst_move.post()
        return advance_debit_aml
    
    def _prepare_settle_statement_line_entry(self, statement):
        values = {
            'statement_id': statement.id,
            'payment_id': self.id,
            'date': self.settlement_date,
            'name': self.name, 
            'partner_id': self.partner_id.id,
            'ref': self.communication or '/',
            'amount': self.residual_total,
        }
        return values
    
    @api.multi
    def post_settle(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #CHANGE STATE ADVANCE WHICH CAN BE POSTED
            if rec.state != 'advance':
                raise UserError(_("Only a advance state can be posted. Trying to post a payment in state %s.") % rec.state)

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = rec.move_line_ids.filtered(lambda r: r.account_id == rec.destination_account_id)
                transfer_debit_aml = rec._create_settlement_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
            #===================================================================
            # CREATE SETTLEMENT LINE
            #===================================================================
            if rec.residual_total <> 0.0 and rec.residual_account_id.user_type_id.type == 'liquidity':
                Statement = self.env['account.bank.statement']
                StatementLine = self.env['account.bank.statement.line']
                statement_id = Statement.search([('journal_id','=',rec.journal_id.id),
                                                 ('date','>=',rec.settlement_date),
                                                 ('date','<=',rec.settlement_date)], limit=1)
                if not statement_id:
                    statement_id = Statement.with_context({'journal_id': rec.journal_id.id}).create({'journal_id': rec.journal_id.id, 'date': rec.settlement_date})
                if statement_id:
                    statement_line_id = StatementLine.create(rec._prepare_settle_statement_line_entry(statement_id))
                    rec.write({'statement_line_id2': statement_line_id.id})
            rec.write({'state': 'settled'})
            
    def _get_settle_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = journal.with_context(ir_sequence_date=self.settlement_date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.settlement_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }        
    

class account_cadvance_line(models.Model):
    _name = 'account.cadvance.line'
    _description = 'Account Advance Line'
    
    payment_id = fields.Many2one('account.payment', string='Payment')
    name = fields.Char(string='Description', required=True)
    amount_to_pay = fields.Float('Amount Advance', required=True, digits=dp.get_precision('Account'))
    company_id = fields.Many2one('res.company', string='Company',
        related='payment_id.company_id', store=True, readonly=True, related_sudo=False)


class account_settlement_line(models.Model):
    _name = 'account.settlement.line'
    _description = 'Account Settlement Line'
    
    payment_id = fields.Many2one('account.payment', string='Payment')
    payment_line_id = fields.Many2one('account.payment.line', string='Payment Line')
    #advance_line_id = fields.Many2one('account.cadvance.line', string='Advance Line')
    name = fields.Char(string='Description', required=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=False, domain=[('deprecated', '=', False),('user_type_id.name','ilike','Expense')],
        help="The income or expense account related to the selected product.")
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    amount_to_pay = fields.Float('Amount Settled', required=True, digits=dp.get_precision('Account'))
    company_id = fields.Many2one('res.company', string='Company',
        related='payment_id.company_id', store=True, readonly=True, related_sudo=False)
    settlement_currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', store=True, related_sudo=False)
    
class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    
    payment_id = fields.Many2one('account.payment', string='Cash Advance')
    