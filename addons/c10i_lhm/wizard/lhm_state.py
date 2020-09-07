from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class lhm_transaction_progress(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "lhm.transaction.progress"
    _description = "Process selected LHM"

    @api.multi
    def run_progress(self):
        context = self._context
        lhm_datas = self.env['lhm.transaction'].browse(context['active_ids'])
        for record in lhm_datas:
            if record.state not in ['draft']:
                raise ValidationError(_('Validate Error!'), _("LHM tersebut tidak dapat di Proses karena tidak berstatus Draft"))
        for lhm in lhm_datas:
            lhm.run_progress()
        return {'type': 'ir.actions.act_window_close'}

lhm_transaction_progress()

class lhm_transaction_set_draft(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "lhm.transaction.set.draft"
    _description = "Set Draft selected LHM"

    @api.multi
    def set_draft(self):
        context = self._context
        lhm_datas = self.env['lhm.transaction'].browse(context['active_ids'])
        for record in lhm_datas:
            if record.state=='close':
                raise ValidationError(_("Anda tidak dapat membatalkan dokumen dalam status Close!"))
        for lhm in lhm_datas:
            if lhm.state=='draft':
                continue
            lhm.button_draft()
        return {'type': 'ir.actions.act_window_close'}

lhm_transaction_set_draft()