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
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime

class Invoice(models.Model):
    _inherit = "account.invoice"

    debit_note_ids = fields.One2many('account.debit.note', 'invoice_id', 'Debit Note', readonly=True)
    dn_count = fields.Integer(compute="_compute_debit_note", string='# of DNs', copy=False, default=0)

    @api.depends('debit_note_ids.state')
    def _compute_debit_note(self):
        for invoice in self:
            invoice.dn_count = len(invoice.debit_note_ids.ids)

    @api.multi
    def action_view_debit_note(self):
        '''
        This function returns an action that display existing debit notes of given invoice ids.
        When only one found, show the debit note immediately.
        '''
        action = self.env.ref('c10i_debit_note.action_debit_note_tree')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'default_invoice_id': self.id}

        if not self.debit_note_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.debit_note_ids[0].journal_id.id

        #choose the view_mode accordingly
        if len(self.debit_note_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.debit_note_ids.ids) + ")]"
        elif len(self.debit_note_ids) == 1:
            res = self.env.ref('c10i_debit_note.debit_note_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.debit_note_ids.id
        return result