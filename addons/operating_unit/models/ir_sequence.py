# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from datetime import datetime, timedelta
import logging
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        # default=lambda self:
        # self.env['res.users'].
        # operating_unit_default_get(self._uid),
    )

    @api.model
    def next_by_code(self, sequence_code):
        """ Draw an interpolated string using a sequence with the requested code.
            If several sequences with the correct code are available to the user
            (multi-company cases), the one from the user's current company will
            be used.

            :param dict context: context dictionary may contain a
                ``force_company`` key with the ID of the company to
                use instead of the user's current company for the
                sequence selection. A matching sequence for that
                specific company will get higher priority.
        """
        self.check_access_rights('read')
        company_ids = self.env['res.company'].search([]).ids + [False]
        seq_ids = self.search(['&', ('code', '=', sequence_code), ('company_id', 'in', company_ids)])
        if not seq_ids:
            _logger.debug("No ir.sequence has been found for code '%s'. Please make sure a sequence is set for current company." % sequence_code)
            return False
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        preferred_sequences = [s for s in seq_ids if s.company_id and s.company_id.id == force_company]
        force_ou = self._context.get('force_operating_unit', False)
        if not force_ou:
            force_ou = self.env.user.default_operating_unit_id and self.env.user.default_operating_unit_id.id or False
        if force_ou:
            if preferred_sequences:
                preferred_sequences = [s for s in preferred_sequences if s.operating_unit_id and s.operating_unit_id.id==force_ou]
            else:
                preferred_sequences = [s for s in seq_ids if s.operating_unit_id and s.operating_unit_id.id==force_ou]
        seq_id = preferred_sequences[0] if preferred_sequences else seq_ids[0]
        return seq_id._next()