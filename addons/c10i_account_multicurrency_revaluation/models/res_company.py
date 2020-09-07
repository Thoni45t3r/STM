# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _

class Company(models.Model):
    _inherit = 'res.company'

    revaluation_loss_account_id = fields.Many2one('account.account', 'Revaluation loss account', domain=[('deprecated', '=', False)])
    revaluation_gain_account_id = fields.Many2one('account.account', 'Revaluation gain account', domain=[('deprecated', '=', False)])
    default_currency_reval_journal_id = fields.Many2one('account.journal', 'Default Revaluation Journal')

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    revaluation_loss_account_id = fields.Many2one('account.account', related='company_id.revaluation_loss_account_id', string='Revaluation loss account', domain=[('deprecated', '=', False)])
    revaluation_gain_account_id = fields.Many2one('account.account', related='company_id.revaluation_gain_account_id', string='Revaluation gain account', domain=[('deprecated', '=', False)])
    default_currency_reval_journal_id = fields.Many2one('account.journal', related='company_id.default_currency_reval_journal_id', string='Default Revaluation Journal', domain=[('type', '=', 'general')])
