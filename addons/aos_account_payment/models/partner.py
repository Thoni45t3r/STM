# -*- coding: utf-8 -*-

from ast import literal_eval
from operator import itemgetter
import time

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def _find_accounting_partner(self, partner):
        commercial_partner = super(ResPartner, self)._find_accounting_partner(partner)
        if self.env.user.company_id.partner_id.id == commercial_partner.id:
            return partner
        else:
            return commercial_partner