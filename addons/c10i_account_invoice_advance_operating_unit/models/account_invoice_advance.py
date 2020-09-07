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

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_advance': 'sale',
    'in_advance': 'purchase',
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class InvoiceAdvance(models.Model):
    _inherit = 'account.invoice.advance'

    operating_unit_id = fields.Many2one('operating.unit', 'Operating Unit',
                                        default=lambda self:
                                        self.env['res.users'].
                                        operating_unit_default_get(self._uid),
                                        readonly=True,
                                        states={'draft': [('readonly',False)]})
    @api.model
    def invoice_line_move_line_get(self):
        res = super(InvoiceAdvance, self).invoice_line_move_line_get()
        for x in res:
            if self.operating_unit_id:
                x.update({'operating_unit_id': self.operating_unit_id.id})
        return res

    @api.model
    def tax_line_move_line_get(self):
        res = super(InvoiceAdvance, self).tax_line_move_line_get()
        for x in res:
            if self.operating_unit_id:
                x.update({'operating_unit_id': self.operating_unit_id.id})
        return res

    @api.multi
    @api.constrains('operating_unit_id', 'company_id')
    def _check_company_operating_unit(self):
        for pr in self:
            if (
                pr.company_id and
                pr.operating_unit_id and
                pr.company_id != pr.operating_unit_id.company_id
            ):
                raise ValidationError(_('The Company in the Invoice and in '
                                        'Operating Unit must be the same.'))
        return True

class InvoiceAdvanceLine(models.Model):
    _inherit = 'account.invoice.advance.line'

    operating_unit_id = fields.Many2one('operating.unit',
                                        related='invoice_id.operating_unit_id',
                                        string='Operating Unit', store=True,
                                        readonly=True)