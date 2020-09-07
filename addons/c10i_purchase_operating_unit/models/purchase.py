# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class PurchaseType(models.Model):
    _inherit = 'purchase.type'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Operating Unit',
        default=lambda self: (self.env['res.users'].
                              operating_unit_default_get(self.env.uid))
    )
    @api.constrains('operating_unit_id','company_id')
    def _check_company_operating_unit(self):
        for record in self:
            if (record.company_id and record.operating_unit_id and
                    record.company_id != record.operating_unit_id.company_id):
                raise ValidationError(
                    _('Configuration error\nThe Company in the Purchase Type '
                      'and in the Operating Unit must be the same.')
                )

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'