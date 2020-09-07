# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
_logger = logging.getLogger(__name__)

class res_afdeling(models.Model):
    _name           = 'res.afdeling'
    _description    = 'Master Afdeling'

    def _default_location_type(self):
        location_type_ids   = self.env['lhm.location.type'].search([('indirect','=',True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active              = fields.Boolean("Active", default=True)

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values = {
            'name'              : location_name or "(NoName)",
            'code'              : location_code or "(NoCode)",
            'type_id'           : location_type_id or False,
            'group_progress_id' : group_progress_id,
        }
        new_location = False
        location = super(res_afdeling, self).create(values)
        if location:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name' : values.get('name',False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code' : values.get('code',False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id' : values.get('location_type_id',False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active' : values.get('active',False)})
        return super(res_afdeling, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(res_afdeling, self).unlink()
        return location


    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, record.code))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result

    @api.multi
    def _name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, record.code + " - " + record.name))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        lhm_location_type = self.search(domain + args, limit=limit)
        return lhm_location_type._name_get()

class res_doc_type(models.Model):
    _name           = 'res.doc.type'
    _description    = 'Document Type'

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    active              = fields.Boolean("Active", default=True)
    approval            = fields.Boolean("With Approval", default=True)
    running_model       = fields.Char("Running Model")
    default_location_type_id = fields.Many2one('lhm.location.type', 'Default Running Location Type')
    account_id          = fields.Many2one('account.account', string='Running Account', index=True)
    contra_account_id   = fields.Many2one('account.account', string='Contra Running Account', index=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

class res_running(models.Model):
    _name           = 'res.running'
    _description    = 'Running Sequence'

    name            = fields.Char("Name")
    line_ids        = fields.One2many(comodel_name='res.running.line', inverse_name="running_id", string="Running Detail")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

_RUNNING_SELECTION = [ \
            ('running', 'Running Account'), ('project', 'Project'), \
            ('nursery', 'Nursery'), ('planting', 'Planting'), \
            ('infrastructure', 'Infrastruktur'), \
            ('other', 'General & Indirect Cost'), \
            ('closing', 'Closing')]

class res_running_line(models.Model):
    _name           = 'res.running.line'
    _description    = 'Running Sequence Line'

    def _get_state(self):
        return list(_RUNNING_SELECTION)

    name                = fields.Char("Name", related="doc_id.name", readonly=True)
    sequence            = fields.Integer("Sequence")
    doc_id              = fields.Many2one(comodel_name="res.doc.type", string="Document Type")
    default_journal_id  = fields.Many2one(comodel_name="account.journal", string="Default Journal")
    running_id          = fields.Many2one(comodel_name="res.running", string="Running")
    run_state           = fields.Selection(selection=_get_state, string='Running State', default='running')