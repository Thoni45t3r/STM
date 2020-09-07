import time
from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
import odoo.addons.decimal_precision as dp
from lxml import etree

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        result = super(AccountMoveLine, self).write(vals)
        for record in self:
            if 'statement_id' in vals and record.payment_id:
                if record.payment_id.advance_ids:
                    if record.payment_id.statement_line_id:
                        record.payment_id.advance_reconciled = True
                    elif not record.payment_id.statement_line_id2 and record.payment_id.statement_line_id:
                        record.payment_id.advance_reconciled = True
                        record.payment_id.state = 'advance'
        return result