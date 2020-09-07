# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression

class PlantationSalaryTargetConfirmation(models.TransientModel):
    _name           = "plantation.salary.target.confirmation"
    _description    = "DU Target Confirmation"

    salary_id = fields.Many2one('plantation.salary')
    restan_found = fields.Boolean('Restan Found')
    tittle = fields.Text('Tittle', readonly=True)
    message = fields.Text('Message', readonly=True)

    @api.one
    def _process(self, cancel_process=False):
        if cancel_process:
            return False
        self.salary_id.generate_data_upah_target()
        self.salary_id.state='confirmed'

    @api.multi
    def process(self):
        self._process()

    @api.multi
    def su_process(self):
        self._process()

    @api.multi
    def process_cancel(self):
        self._process(cancel_process=True)