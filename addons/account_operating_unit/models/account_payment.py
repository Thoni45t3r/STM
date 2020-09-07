# -*- coding: utf-8 -*-
# © 2016-17 Eficent Business and IT Consulting Services S.L.
# © 2016 Serpent Consulting Services Pvt. Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('journal_id')
    def _compute_operating_unit_id(self):
        for payment in self:
            if payment.journal_id:
                payment.operating_unit_id = \
                    payment.journal_id.operating_unit_id

    operating_unit_id = fields.Many2one(
        'operating.unit', string='Operating Unit',
        compute='_compute_operating_unit_id', readonly=True, store=True)

    def _get_counterpart_move_line_vals(self, invoice=False):
        res = super(AccountPayment,
                    self)._get_counterpart_move_line_vals(invoice=invoice)
        if len(invoice) == 1:
            res['operating_unit_id'] = invoice.operating_unit_id.id or False
        else:
            res['operating_unit_id'] = self.operating_unit_id.id or False
        return res

    def _get_liquidity_move_line_vals(self, amount):
        res = super(AccountPayment, self)._get_liquidity_move_line_vals(amount)
        res['operating_unit_id'] = self.journal_id.operating_unit_id.id \
            or False
        return res

    def _get_dst_liquidity_aml_dict_vals(self):
        dst_liquidity_aml_dict = {
            'name': _('Transfer from %s') % self.journal_id.name,
            'account_id':
                self.destination_journal_id.default_credit_account_id.id,
            'currency_id': self.destination_journal_id.currency_id.id,
            'payment_id': self.id,
            'journal_id': self.destination_journal_id.id,
        }

        if self.currency_id != self.company_id.currency_id:
            dst_liquidity_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': self.amount,
            })

        dst_liquidity_aml_dict.update({
            'operating_unit_id':
                self.destination_journal_id.operating_unit_id.id or False})
        return dst_liquidity_aml_dict

    def _get_transfer_debit_aml_dict_vals(self):
        transfer_debit_aml_dict = {
            'name': self.name,
            'payment_id': self.id,
            'account_id': self.company_id.transfer_account_id.id,
            'journal_id': self.destination_journal_id.id
        }
        if self.currency_id != self.company_id.currency_id:
            transfer_debit_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
            })
        transfer_debit_aml_dict.update({
            'operating_unit_id':
                self.journal_id.operating_unit_id.id or False
        })
        return transfer_debit_aml_dict

    def _create_transfer_entry(self, amount):
        """ We need to override the standard method, until proper hooks are
        created
        """
        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)
        debit, credit, amount_currency, dummy = aml_obj.with_context(
            date=self.payment_date).compute_amount_fields(
            amount, self.currency_id, self.company_id.currency_id)
        amount_currency = self.destination_journal_id.currency_id \
            and self.currency_id.with_context(date=self.payment_date).compute(
                amount, self.destination_journal_id.currency_id) or 0

        dst_move = self.env['account.move'].create(
            self._get_move_vals(self.destination_journal_id))

        dst_liquidity_aml_dict = self._get_shared_move_line_vals(
            debit, credit, amount_currency, dst_move.id)
        dst_liquidity_aml_dict.update(self._get_dst_liquidity_aml_dict_vals())
        aml_obj.create(dst_liquidity_aml_dict)

        transfer_debit_aml_dict = self._get_shared_move_line_vals(
            credit, debit, 0, dst_move.id)
        transfer_debit_aml_dict.update(
            self._get_transfer_debit_aml_dict_vals())
        transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
        dst_move.post()
        return transfer_debit_aml

    def _create_payment_entry_multi(self, amount, invoice, move, line):
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = invoice.currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date,
            force_rate=self.force_rate).compute_amount_fields(
            amount, self.currency_id, self.company_id.currency_id, invoice_currency)
        # =======================================================================
        # GET RATE FROM INVOICE DATE
        # WHY LIKE THIS
        # debit_inv, credit_inv, amount_currency_inv, currency_inv_id = aml_obj.with_context(date=invoice.date_invoice).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, invoice_currency)
        # =======================================================================
        # Write line corresponding to invoice payment
        # if invoice:
        # counterpart_aml_dict = self._get_shared_move_line_vals(debit_inv, credit_inv, amount_currency_inv, move.id, False)
        # else:
        # counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        # counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, invoice)
        # print "===counterpart_aml_dict===",line.invoice_id
        counterpart_aml_dict.update(
            self.with_context(payment_line=True, move_line=line.move_line_id)._get_counterpart_move_line_vals(
                line.invoice_id))
        counterpart_aml_dict.update(
            {'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        # =======================================================================
        # CREATE EXCHANGE RATE ONLY FOR PARTIAL PAYMENT
        # =======================================================================
        # WHAT IS THIS
        # if self.payment_type == 'inbound':
        #     amount_diff = credit_inv-credit
        # elif self.payment_type == 'outbound':
        #     amount_diff = debit_inv-debit
        # if (amount_diff) != 0:
        #     exch_diff = {
        #         'name': _('Currency exchange rate difference'),
        #         'debit': amount_diff > 0 and amount_diff or 0.0,
        #         'credit': amount_diff < 0 and -amount_diff or 0.0,
        #         'account_id': amount_diff > 0 and self.company_id.currency_exchange_journal_id.default_debit_account_id.id or self.company_id.currency_exchange_journal_id.default_credit_account_id.id,
        #         'move_id': move.id,
        #         'invoice_id': invoice and invoice.id or False,
        #         'payment_id': self.id,
        #         'currency_id': False,
        #         'amount_currency': 0,
        #         'partner_id': invoice and invoice.partner_id.id,
        #     }
        #     aml_obj.create(exch_diff)
        # ===================================================================
        # Reconcile with the invoices each
        if line.payment_difference and line.writeoff_account_id:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date,
                force_rate=self.force_rate).compute_amount_fields(
                line.payment_difference, line.currency_id, self.company_id.currency_id, invoice_currency)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = line.invoice_id.residual_company_signed  # sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(
                line.amount_to_pay, self.company_id.currency_id)
            if line.invoice_id.type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            debit_wo = amount_wo > 0 and amount_wo or 0.0
            credit_wo = amount_wo < 0 and -amount_wo or 0.0
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = line.writeoff_account_id.id
            writeoff_line['payment_id'] = self.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            if line.invoice_id.operating_unit_id:
                writeoff_line['operating_unit_id'] = line.invoice_id.operating_unit_id.id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
            # self.invoice_ids.register_payment(counterpart_aml)
            # if invoice:
            #     invoice.register_payment(counterpart_aml, line.writeoff_account_id, self.journal_id)
            # else:
            #     if not invoice and line.move_line_id:
            #         (line.move_line_id + counterpart_aml).reconcile(line.writeoff_account_id, self.journal_id)
            line.reconcile_payment_line(counterpart_aml, line.writeoff_account_id, self.journal_id)
        else:
            # if invoice:
            #     invoice.register_payment(counterpart_aml)
            # else:
            #     if not invoice and line.move_line_id:
            #         (line.move_line_id + counterpart_aml).reconcile()
            line.reconcile_payment_line(counterpart_aml)