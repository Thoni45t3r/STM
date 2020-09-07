# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import models, api, _
from odoo.exceptions import UserError

class AssetConfirm(models.TransientModel):
    _name = "wizard.asset.confirm"
    _description = "Confirm the selected Assets"

    @api.multi
    def confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['account.asset.asset'].browse(active_ids):
            if record.state!='draft':
                raise UserError(_("Selected Asset(s) cannot be confirmed as they are not in 'Draft' state."))
            record.validate()
        return {'type': 'ir.actions.act_window_close'}