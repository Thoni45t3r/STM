# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class res_document_type(models.Model):
    _name           = 'res.document.type'
    _description    = 'Document Type'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']

    name                    = fields.Char("Name")
    sales                   = fields.Boolean("Is Sales?")
    spk                     = fields.Boolean("Is SPK?")
    no_create_picking       = fields.Boolean("No Create Picking?")
    auto_downpayment        = fields.Boolean("Auto Downpayment")
    sequence_id             = fields.Many2one("ir.sequence", "Sequence", ondelete="restrict")
    report_id               = fields.Many2one("ir.actions.report.xml", "Report", ondelete="restrict")
    journal_id              = fields.Many2one("account.journal", "Journal", ondelete="restrict")
    account_id              = fields.Many2one("account.account", "Account", ondelete="restrict")
    downpayment_journal_id  = fields.Many2one("account.journal", "Down Payment Journal", ondelete="restrict")
    downpayment_account_id  = fields.Many2one("account.account", "Down Payment Account", ondelete="restrict")
    downpayment_default     = fields.Float("Default Down Payment", default=15)
    payment_term_id         = fields.Many2one("account.payment.term", "Payment Term", ondelete="restrict")
    incoterm_id             = fields.Many2one("stock.incoterms", "Incoterm", ondelete="restrict")
    picking_type_id         = fields.Many2one("stock.picking.type", "Picking Type", ondelete="restrict")
    tolerance               = fields.Float("Tolerance")
    shipping_partner_id     = fields.Many2one('res.partner', 'Delivery Address')
    invoice_partner_id 	    = fields.Many2one('res.partner', 'Invoice Address')
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    user_ids                = fields.Many2many('res.users', 'document_user_rel', 'document_id', 'user_id', string='Users')
    purchase_report_sign_1  = fields.Char("Sign 1", default="Purchasing")
    purchase_report_sign_2  = fields.Char("Sign 2", default="Accounting")
    purchase_report_sign_3  = fields.Char("Sign 3", default="Accounting")
    purchase_report_sign_4  = fields.Char("Sign 4", default="Accounting")
    purchase_report_sign_5  = fields.Char("Sign 5", default="Finance")
    purchase_report_sign_6  = fields.Char("Sign 6", default="Finance")