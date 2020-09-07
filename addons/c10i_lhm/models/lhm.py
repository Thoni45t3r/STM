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
import time
import datetime
import calendar
from odoo.tools.translate import _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import base64
import xlrd

BULAN_INDONESIA = [('1', 'Januari'),
                   ('2', 'Februari'),
                   ('3', 'Maret'),
                   ('4', 'April'),
                   ('5', 'Mei'),
                   ('6', 'Juni'),
                   ('7', 'Juli'),
                   ('8', 'Agustus'),
                   ('9', 'September'),
                   ('10', 'Oktober'),
                   ('11', 'November'),
                   ('12', 'Desember')]
TAHUN           = [(num, str(num)) for num in range((datetime.datetime.now().year) - 30, (datetime.datetime.now().year) + 1)]

#---------------------------------------------------------------------------------------------------------------------------#
#############################################################################################################################
#
#   This is for Configuration Models
#
#############################################################################################################################
#---------------------------------------------------------------------------------------------------------------------------#
#################################################### Config Location Type ###################################################
class lhm_location_type(models.Model):
    _name           = 'plantation.location.reference'
    _description    = 'Plantation Location Reference'
    _order          = 'code, name'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    active          = fields.Boolean("Active", default=True)
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

class lhm_location_type(models.Model):
    _name           = 'lhm.location.type'
    _description    = 'LHM Location Type'
    _order          = 'code, name'

    name                    = fields.Char("Name")
    code                    = fields.Char("Code")
    active                  = fields.Boolean("Active", default=True)
    indirect                = fields.Boolean("Indirect", default=False)
    general_charge          = fields.Boolean("General Charge", default=False)
    infrastruktur           = fields.Boolean("Infrastruktur", default=False)
    machine                 = fields.Boolean("Machine", default=False)
    nursery                 = fields.Boolean("Nursery", default=False)
    oil_palm                = fields.Boolean("Oil Palm", default=False)
    project                 = fields.Boolean("Project", default=False)
    vehicle                 = fields.Boolean("Vehicle", default=False)
    workshop                = fields.Boolean("Workshop", default=False)
    workshop_line           = fields.Boolean("Workshop Line", default=False, help="Centang jika tipe lokasi ingin ditampilkan di Buku Workshop")
    machine_line            = fields.Boolean("Machine Line", default=False, help="Centang jika tipe lokasi ingin ditampilkan di Buku Mesin")
    no_line                 = fields.Boolean("No Line", default=False, help="Centang jika tipe lokasi tidak ingin ditampilkan di Dokumen Plantation Manapun")
    skb_declare             = fields.Boolean("SKB Declare", default=False)
    has_subtype             = fields.Boolean("Sub Tipe?", help="Centang jika memiliki sub tipe")
    # account_activity        = fields.Boolean("Use Account From Activity?", help="Langsung menggunakan account dari aktivitas")
    account_id              = fields.Many2one(comodel_name="account.account", string="Allocation", ondelete="restrict")
    location_ids            = fields.One2many(comodel_name="lhm.location", inverse_name="type_id", string="Daftar Lokasi", )
    activity_ids            = fields.One2many(comodel_name="lhm.activity", inverse_name="type_id", string="Daftar Aktivitas", )
    subtype_ids             = fields.One2many(comodel_name="lhm.sub.location.type", inverse_name="type_id", string="Daftar Sub Type Location")
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    beban_closing_account_id = fields.Many2one('account.account', 'Beban Alokasi Closing Account (Default)')

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
################################################## End Config Location Type #################################################
################################################# Config Sub Type Location ##################################################
class lhm_sub_location_type(models.Model):
    _name           = 'lhm.sub.location.type'
    _description    = 'LHM Sub Type Location'

    name        = fields.Char("Name")
    code        = fields.Char("Code")
    type_id     = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active      = fields.Boolean("Active", default=True)
############################################## End Of Config Sub Type Location ##############################################
###################################################### Config Location ######################################################
class lhm_location(models.Model):
    _name           = 'lhm.location'
    _description    = 'LHM Location'

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    type_id             = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active              = fields.Boolean("Active", default=True)
    owner_type          = fields.Selection([('inti','Inti'),('plasma','Plasma')], 'Tipe Kepemilikan Blok')
    
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
        lhm_location = self.search(domain + args, limit=limit)
        return lhm_location._name_get()
#################################################### End Config Location ####################################################
######################################################## Config Uom #########################################################
# class lhm_uom(models.Model):
#     _name           = 'lhm.uom'
#     _description    = 'LHM UOM Management'
#
#     name            = fields.Char("Name")
#     code            = fields.Char("Code")
#     rounding        = fields.Float("Pembulatan")
#     factor          = fields.Float("Pengali")
#     active          = fields.Boolean("Active", default=True)
#     company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
#
#     @api.multi
#     def name_get(self):
#         result = []
#         for record in self:
#             if record.name and record.code:
#                 result.append((record.id, record.code))
#             if record.name and not record.code:
#                 result.append((record.id, record.name))
#         return result
#
#     @api.multi
#     def _name_get(self):
#         result = []
#         for record in self:
#             if record.name and record.code:
#                 result.append((record.id, record.code + " - " + record.name))
#             if record.name and not record.code:
#                 result.append((record.id, record.name))
#         return result
#
#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         args = args or []
#         domain = []
#         if name:
#             domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
#             if operator in expression.NEGATIVE_TERM_OPERATORS:
#                 domain = ['&', '!'] + domain[1:]
#         lhm_uom = self.search(domain + args, limit=limit)
#         return lhm_uom._name_get()
# ###################################################### End Config Uom #######################################################
################################################### Config Beban Muatan #####################################################
class lhm_charge_type(models.Model):
    _name           = 'lhm.charge.type'
    _description    = 'LHM Charge Type'

    name        = fields.Char("Nama")
    code        = fields.Char("Kode")
    uom_id      = fields.Many2one(comodel_name="product.uom", string="Satuan", ondelete="restrict")
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active      = fields.Boolean("Active", default=True)
############################################### End Of Config Beban Muatan ##################################################
################################################### Config Kelas Lahan ######################################################
class lhm_land_class(models.Model):
    _name           = 'lhm.land.class'
    _description    = 'Kelas Lahan'

    name        = fields.Char("Name")
    code        = fields.Char("Code")
    active      = fields.Boolean("Active", default=True)
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
############################################### End Of Config Kelas Lahan ###################################################
############################################# Config Kecambah Kelapa Sawit ##################################################
class lhm_palm_oil_sprouts(models.Model):
    _name           = 'lhm.palm.oil.sprouts'
    _description    = 'Kecambah Kelapa Sawit'

    name        = fields.Char("Name")
    code        = fields.Char("Code")
    active      = fields.Boolean("Active", default=True)
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
########################################## End Of Config Kecambah Kelapa Sawit ##############################################
############################################## Config Berat Janjang Rata-Rata ###############################################
class lhm_restan_balace(models.Model):
    _name           = 'lhm.restan.balance'
    _description    = 'LHM Restan Saldo Awal'

    tgl_panen = fields.Date(" Tanggal Panen")
    block_id = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi", ondelete="restrict")
    value = fields.Float('Saldo Awal (Janjang)')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
########################################### End Of Config Berat Janjang Rata-Rata  ##########################################
#---------------------------------------------------------------------------------------------------------------------------#
#############################################################################################################################
#
#   This is for Master Models
#
#############################################################################################################################
#---------------------------------------------------------------------------------------------------------------------------#
###################################################### Master Activity ######################################################
class lhm_activity(models.Model):
    _name           = 'lhm.activity'
    _description    = 'LHM Activity Management'

    name            = fields.Char("Name")
    code            = fields.Char("Code")
    type_id         = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    parent_id       = fields.Many2one(comodel_name="lhm.activity", string="Parent Activity", ondelete="restrict")
    child_ids       = fields.One2many('lhm.activity', 'parent_id', 'Child Activity')
    parent_left     = fields.Integer('Left Parent', index=1)
    parent_right    = fields.Integer('Right Parent', index=1)
    parent_code     = fields.Char(related="parent_id.code", string="Parent Activity", readonly=True, store=True)
    uom_id          = fields.Many2one(comodel_name="product.uom", string="Satuan 1", ondelete="restrict")
    uom2_id         = fields.Many2one(comodel_name="product.uom", string="Satuan 2", ondelete="restrict")
    active          = fields.Boolean("Active", default=True)
    is_panen        = fields.Boolean("Panen", default=False)
    is_variance     = fields.Boolean("Is Variance?", default=False, help="centang untuk menghitung variance di laporan progress kerja")
    skb             = fields.Boolean("Is SKB?", default=False, help="centang untuk aktivitas yang akan divalidasi untuk penggunaan material")
    bypass          = fields.Boolean("Is By Pass?", default=False, help="centang untuk aktivitas tidak akan dirunning")
    vh2vh           = fields.Boolean("VH to VH", default=False, help="centang untuk aktivitas khusus untuk running kendaraan ke kendaraan")
    level           = fields.Integer("Level", compute="_compute_level", readonly=True, store=True)
    doc_ids         = fields.Many2many('res.doc.type', 'rel_doc_type_activity', 'activity_id', 'doc_type_id', string='Documents')
    charge_ids      = fields.Many2many('lhm.charge.type', 'rel_chg_type_activity', 'activity_id', 'charge_id', string='Muatan')
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    account_id                                  = fields.Many2one(comodel_name="account.account", string="Allocation", ondelete="restrict")
    beban_closing_account_id                    = fields.Many2one('account.account', 'Beban Closing Account (TBM)')
    tm_beban_closing_account_id                 = fields.Many2one('account.account', 'Beban Closing Account (TM) - Inti')
    tm_plasma_closing_account_id                = fields.Many2one('account.account', 'Beban Closing Account (TM) - Plasma')
    counterpart_closing_account_id              = fields.Many2one('account.account', 'Kontra Closing Account TBM')
    tm_counterpart_closing_account_id           = fields.Many2one('account.account', 'Kontra Closing Account TM - Inti')
    tm_plasma_counterpart_closing_account_id    = fields.Many2one('account.account', 'Kontra Closing Account TM - Plasma')

    _parent_name    = "parent_id"
    _parent_store   = True
    _parent_order   = 'code, name'
    _order          = 'code, parent_left asc'

    @api.one
    @api.depends('parent_id')
    def _compute_level(self):
        for level in self:
            self.level = len(self.search([('id', 'parent_of', [self.id])]))

    @api.multi
    def _get_account(self):
        self.ensure_one()
        res = False
        if self.account_id:
            res = self.account_id
        elif self.parent_id:
            res = self._get_account(self.parent_id)
        else:
            res = self.type_id and self.type_id.account_id or False
        return res

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, '%s %s'%(record.code, record.name)))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result

    @api.multi
    def _name_get(self):
        result = []
        for record in self:
            if record.name and record.code:
                result.append((record.id, record.code + " " + record.name))
            if record.name and not record.code:
                result.append((record.id, record.name))
        return result


    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account code
        instead of its name. In that case, switch both fields values.
        """
        default_name = self._context.get('default_name')
        default_code = self._context.get('default_code')
        if default_name and not default_code:
            try:
                default_code = int(default_name)
            except ValueError:
                pass
            if default_code:
                default_name = False
        contextual_self = self.with_context(default_name=default_name, default_code=default_code)
        return super(lhm_activity, contextual_self).default_get(default_fields)


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        lhm_activity = self.search(domain + args, limit=limit)
        return lhm_activity._name_get()
#################################################### End Master Activity ####################################################
################################################### Master Indirect Cost ####################################################
class plantation_indirect_cost(models.Model):
    _name           = 'plantation.indirect.cost'
    _description    = 'Master Plantation Indirect Cost'

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
        location = super(plantation_indirect_cost, self).create(values)
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
        return super(plantation_indirect_cost, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(plantation_indirect_cost, self).unlink()
        return location
################################################# End Master Indirect Cost ##################################################
####################################################### Master Utility ######################################################
class lhm_utility(models.Model):
    _name           = 'lhm.utility'
    _description    = 'LHM Utility Management'

    def _default_location_type(self):
        location_type_ids = False
        if self._context.get('default_type',False):
            type    = self._context.get('default_type')
            if type == 'ws':
                location_type_ids   = self.env['lhm.location.type'].search([('workshop','=',True)])
            elif type == 'vh':
                location_type_ids   = self.env['lhm.location.type'].search([('vehicle','=',True)])
            elif type == 'ma':
                location_type_ids   = self.env['lhm.location.type'].search([('machine','=',True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    name                = fields.Char("Name")
    code                = fields.Char("Code")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    reg_number          = fields.Char("Nomor Polisi")
    asset_id            = fields.Many2one('account.asset.asset', string='Asset', ondelete="restrict")
    ownership           = fields.Selection([('inventory', 'Inventaris'), ('rental', 'Rental')], string='Kepemilikan', default='inventory')
    partner_id          = fields.Many2one('res.partner', 'Vendor')
    uom_performance     = fields.Selection([('km', 'KM'), ('hm', 'HM')], string='Satuan', default='km')
    type                = fields.Selection([('ws', 'Workshop'), ('vh', 'Vehicle'), ('ma', 'Machine')], string='Type')
    responsible_id      = fields.Many2one(comodel_name="hr.employee", string="PIC", ondelete="restrict")
    date_purchase       = fields.Date(string="Tanggal Pembelian")
    date_approve        = fields.Date(string="Tanggal Pengesahan")
    approve_by          = fields.Many2one(comodel_name="hr.employee", string="Disahkan Oleh", ondelete="restrict")
    active              = fields.Boolean("Active", default=True)
    company_id          = fields.Many2one(comodel_name='res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

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

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values     = {
            'name'              : location_name or "(NoName)",
            'code'              : location_code or "(NoCode)",
            'type_id'           : location_type_id or False,
            'group_progress_id' : group_progress_id,
        }
        new_location = False
        location = super(lhm_utility, self).create(values)
        if location:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(lhm_utility, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(lhm_utility, self).unlink()
        return location
################################################### End Of Master Utility ###################################################
##################################################### Master Blok Tanah #####################################################
class lhm_land_block(models.Model):
    _name           = 'lhm.land.block'
    _description    = 'Blok Tanah'

    name        = fields.Char("Name")
    code        = fields.Char("Code")
    active      = fields.Boolean("Active", default=True)
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

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
############################################### End Of Master Blok Tanah ####################################################
################################################### Master Blok Tanam #######################################################
class lhm_plant_block(models.Model):
    _name           = 'lhm.plant.block'
    _description    = 'LHM Planting Block'

    def _default_location_type(self):
        location_type_ids   = self.env['lhm.location.type'].search([('oil_palm','=',True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    def _default_year(self):
        return int(time.strftime('%Y'))

    @api.multi
    @api.depends('year', 'tm_year')
    def _compute_time_plant(self):
        for block in self:
            current_year = int(time.strftime('%Y'))
            block_age = int(time.strftime('%Y')) - block.year
            if block.tm_year:
                block.status = 'tm'
                block.tm_age = 'TM%s'%str(current_year - block.tm_year + 1)
                block.tbm_age = 'TBM%s'%str(block.tm_year - block.year - 1)
                block.planting_time = block_age 
                block.tm_category = (block_age + 1) < 8 and 'young' or ((block_age + 1)>=8 and (block_age)<=18 and 'prime' or 'old')
                block.need_to_be_approved = False
            else:
                block.status = 'tbm'
                block.planting_time = block_age 
                block.tm_age = ''
                block.tbm_age = 'TBM%s'%str(block_age and 0 or block_age - 1)
                block.tm_category = False
                if block_age >= 4:
                    block.need_to_be_approved = True
            
    name                = fields.Char("Deskripsi")
    code                = fields.Char("Kode")
    land_block_id       = fields.Many2one(comodel_name="lhm.land.block", string="Blok Tanah", ondelete="restrict")
    afdeling_id         = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    owner_type          = fields.Selection([('inti','Inti'),('plasma','Plasma')], 'Tipe Kepemilikan')
    plasma_pricelist_id = fields.Many2one('product.pricelist', 'Harga TBS Plasma')
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    planted             = fields.Float("Planted")
    plantable           = fields.Float("Plantable")
    koefisien_luas      = fields.Float("Koefisien Luasan")
    total_plant         = fields.Float("Jumlah Pokok")
    status              = fields.Selection(selection=[('tbm','Tanaman Belum Menghasilkan'),('tm','Tanaman Menghasilkan')],string="Status", compute="_compute_time_plant", store=True)
    need_to_be_approved = fields.Boolean('Butuh Approval untuk masuk ke Kategori Tanaman Menghasilkan', compute='_compute_time_plant', store=True)
    tm_year             = fields.Selection(TAHUN, string='Tahun Menjadi TM')
    tm_category         = fields.Selection([('young', 'Young'), ('prime', 'Prime'), ('old','Old')], string='TM Category', compute='_compute_time_plant', store=True)
    tm_age              = fields.Char('Umur TM', compute='_compute_time_plant', store=True)
    tbm_age             = fields.Char('Umur TBM', compute='_compute_time_plant', store=True)
    planting_time       = fields.Integer(string="Lama Tanam", compute="_compute_time_plant", store=True)
    block_uom           = fields.Many2one(comodel_name='product.uom', string="Satuan")
    date_start          = fields.Date('Tanggal Awal Tanam')
    year                = fields.Selection(TAHUN, string='Tahun Tanam', default=_default_year)
    land_class_id       = fields.Many2one(comodel_name="lhm.land.class", string="Kelas Lahan", ondelete="restrict")
    sprouts_id          = fields.Many2one(comodel_name="lhm.palm.oil.sprouts", string="Kecambah Kelapa Sawit", ondelete="restrict")
    section             = fields.Char("Seksi")
    active              = fields.Boolean("Active", default=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    
    _sql_constraints = [('name_company_uniq', 'unique (name, company_id)', "Blok Tanam Sudah ada percompany!"),]

    @api.model
    def _get_rate_bjr(self):
        context = self.env.context
        rate = self.env['lhm.bjr'].search([('block_id','=',self.id), ('date','<=', context.get('date', time.strftime('%Y-%m-%d')))])
        return rate and rate[-1].value or 0.0

    @api.onchange('afdeling_id')
    def _onchange_afdeling_id(self):
        if self.afdeling_id:
            self.block = self.afdeling_id.code or False

    @api.multi
    def button_set_as_tm(self):
        self.status = 'tm'
        self.tm_year = int(time.strftime('%Y'))

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values     = {
            'name'              : location_name or "(NoName)",
            'code'              : location_code or "(NoCode)",
            'type_id'           : location_type_id or False,
            'group_progress_id' : group_progress_id,
        }
        new_location    = False
        location        = super(lhm_plant_block, self).create(values)
        if location:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(lhm_plant_block, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(lhm_plant_block, self).unlink()
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

    @api.model
    def _cron_update_tahun_tanam(self):
        blocks_to_check = self.search([('id','>',0)])
        for block in blocks_to_check:
            # Triggering Function Field to be Executed to check and update Block Status
            block.write({'year': block.year})
        
################################################## End Of Master Blok Tanam #################################################
#################################################### Master Blok Bibitan ####################################################
class lhm_nursery(models.Model):
    _name           = 'lhm.nursery'
    _description    = 'LHM Nursery'

    def _default_location_type(self):
        location_type_ids = self.env['lhm.location.type'].search([('nursery', '=', True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    name                = fields.Char("Deskripsi")
    code                = fields.Char("Kode Batch")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Type Lokasi", ondelete="restrict", default=_default_location_type)
    date                = fields.Date("Periode Batch")
    varietas            = fields.Char("Varietas")
    qty                 = fields.Float("Jumlah")
    active              = fields.Boolean("Active", default=True)
    group_progress_id   = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    account_id          = fields.Many2one("account.account", "Cost Account")

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values     = {
                                'name'              : location_name or "(NoName)",
                                'code'              : location_code or "(NoCode)",
                                'type_id'           : location_type_id or False,
                                'group_progress_id' : group_progress_id,
                            }
        new_location    = False
        location        = super(lhm_nursery, self).create(values)
        if location:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(lhm_nursery, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(lhm_nursery, self).unlink()
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
################################################# End Of Master Blok Bibitan ################################################
#################################################### Master Infrastruktur ###################################################
class lhm_infrastruktur(models.Model):
    _name           = 'lhm.infrastruktur'
    _description    = 'LHM Infrastruktur'

    def _default_location_type(self):
        location_type_ids = self.env['lhm.location.type'].search([('infrastruktur', '=', True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    name                    = fields.Char("Deskripsi")
    location_id             = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id        = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict", default=_default_location_type)
    location_subtype_id     = fields.Many2one(comodel_name="lhm.sub.location.type", string="Subtipe", ondelete="restrict")
    group_progress_id       = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    code                    = fields.Char("Kode")
    afdeling_id             = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    length                  = fields.Float("Panjang")
    width                   = fields.Float("Lebar")
    satuan_id               = fields.Many2one(comodel_name="product.uom", string="Satuan", ondelete="restrict")
    volume                  = fields.Float("Volume")
    date_finished           = fields.Date("Tanggal Selesai")
    development_value       = fields.Float("Biaya")
    active_rm               = fields.Boolean("Active RM", default=False)
    charge_type             = fields.Selection([('op', 'Oil Palm'), ('gc', 'General Charge'), ('idc', 'Indirect Cost')], string='Tipe Pembebanan')
    charge_op_id            = fields.Many2one(comodel_name="lhm.land.block", string="Charge Oil Palm")
    charge_gc_id            = fields.Many2one(comodel_name="account.cost.center", string="Charge General Charge")
    charge_idc_id           = fields.Many2one(comodel_name="res.afdeling", string="Charge Indirect Cost")

    beban_infras_account_id = fields.Many2one('account.account', 'Beban Infrastruktur (Default)', \
        help='Akun ini akan digunakan sebagai akun Beban ketika Running Account dan dilawankan pada Kontra Akun Infrastruktur')
    tm_beban_infras_account_id = fields.Many2one('account.account', 'Beban Infrastruktur (Oil Palm Blok TM)', \
        help='Terkhusus pada Pembebanan Oil Palm, akun ini akan digunakan apabila Status Blok Tanam telah menjadi Tanaman Menghasilkan. \n \
            Jika akun ini kosong maka Pembebanan Oil Palm akan masuk ke akun pertama Beban Infrastruktur')
    counterpart_expense_account_id = fields.Many2one('account.account', 'Kontra Beban Infrastruktur', 
        help='Akun ini akan digunakan sebagai lawan akun Beban Infrastruktur')
    active                  = fields.Boolean("Active", default=True)
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, values):
        location_name       = values.get('name', False)
        location_code       = values.get('code', False)
        location_type_id    = values.get('location_type_id', False)
        group_progress_id   = values.get('group_progress_id', False)
        location_values     = {
            'name': location_name or "(NoName)",
            'code': location_code or "(NoCode)",
            'type_id': location_type_id or False,
            'group_progress_id': group_progress_id,
        }
        new_location    = False
        location        = super(lhm_infrastruktur, self).create(values)
        if location:
            new_location = self.env['lhm.location'].create(location_values)
        if new_location:
            location.location_id = new_location.id
        return location

    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'name': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'code': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'group_progress_id' in values and self.location_id:
            self.location_id.write({'group_progress_id' : values.get('group_progress_id',False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(lhm_infrastruktur, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(lhm_infrastruktur, self).unlink()
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
################################################ End Of Master Infrastruktur ################################################
###################################################### Master Project #######################################################
class lhm_project_type(models.Model):
    _name           = 'lhm.project.type'
    _description    = 'LHM Project Category'

    name = fields.Char('Name', required=True)
    account_id = fields.Many2one('account.account', 'Expense Account', required=True)

class lhm_project(models.Model):
    _name           = 'lhm.project'
    _description    = 'LHM Project'

    def _default_location_type(self):
        location_type_ids = self.env['lhm.location.type'].search([('project', '=', True)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    def _default_dest_location_type(self):
        location_type_ids = self.env['lhm.location.type'].search([('project', '=', False)])
        if location_type_ids:
            return location_type_ids[0].id
        else:
            return False

    @api.model
    def _get_user_currency(self):
        currency_id = self.env['res.users'].browse(self._uid).company_id.currency_id
        return currency_id or self.company_id.currency_id

    @api.one
    @api.depends('line_ids.value', 'line_ids.vat')
    def _compute_project_value(self):
        total_vat   = 0
        total_value = 0
        for line in self.line_ids:
            if line.vat >= 1 and line.value >=1:
                total_vat += (line.vat * line.value)/100
            if line.value:
                total_value += line.value
        self.project_value  = total_value
        self.project_ppn    = total_vat
        self.project_nett   = total_vat + total_value

    name                    = fields.Char("Deskripsi")
    code                    = fields.Char("Nomor Project")
    afdeling_id             = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    location_id             = fields.Many2one(comodel_name="lhm.location", string="Lokasi")
    location_type_id        = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi Project", ondelete="restrict", default=_default_location_type)
    dest_location_type_id   = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi Tujuan", ondelete="restrict", default=_default_dest_location_type)
    location_code           = fields.Char("Kode Lokasi", related="location_id.code")
    executor                = fields.Selection([('swakelola', 'Swakelola'), ('contractor', 'Kontraktor')], string='Pelaksana')
    pk_number               = fields.Char("Nomor PK")
    date_start              = fields.Date("Tanggal Mulai")
    date_finished           = fields.Date("Tanggal Selesai")
    qty                     = fields.Float("Qty")
    satuan_id               = fields.Many2one(comodel_name="product.uom", string="Satuan", ondelete="restrict")
    project_value           = fields.Float("Nilai", compute="_compute_project_value", store=False)
    project_ppn             = fields.Float("PPN", compute="_compute_project_value", store=False)
    project_nett            = fields.Float("Nilai Nett", compute="_compute_project_value", store=False)
    date_issue              = fields.Date("Tanggal Terbit")
    active                  = fields.Boolean("Active", default=True)
    note                    = fields.Text("Catatan")
    line_ids                = fields.One2many('lhm.project.line', 'project_id', string="Detail Project", )
    group_progress_id       = fields.Many2one(comodel_name="plantation.location.reference", string="Grouping LPPH")
    currency_id             = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._get_user_currency())
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state                   = fields.Selection(selection=[('draft','New'),('cancel','Cancelled'),('in_progress','Progress'),('done','Done')],
                                                string='Status', copy=False, default='draft', index=False, readonly=False,
                                                help="* New: Project baru.\n"
                                                    "* Cancelled: Project Dibatalkan.\n"
                                                    "* Progress: Project sedang dalam Proses.\n"
                                                    "* Done: Project Sudah Selesai. \n")
    categ_id                = fields.Many2one('lhm.project.type', 'Kategory')

    @api.multi
    def button_progress(self):
        if not self.location_id:
            location_name       = self.code
            location_code       = self.name
            location_type_id    = self.location_type_id
            location_values     = {
                'name'      : location_name or "(NoName)",
                'code'      : location_code or "(NoCode)",
                'type_id'   : location_type_id and location_type_id.id or False,
            }
            new_location = self.env['lhm.location'].create(location_values)
            if new_location:
                 self.location_id = new_location.id
        else:
            self.location_id.write({'active': True})
        self.state = 'in_progress'

    @api.multi
    def button_cancel(self):
        if self.location_id:
            self.location_id.write({'active': False})
        self.state = 'cancel'

    @api.multi
    def button_draft(self):
        if self.location_id:
            self.location_id.write({'active': False})
        self.state = 'draft'

    @api.multi
    def button_done(self):
        if self.location_id:
            self.location_id.write({'active': True})
        self.state = 'done'

    @api.onchange('location_type_id')
    def onchange_attendance_id(self):
        res = {}
        if self.location_type_id:
            self.subtype_project_id = False
        return res

    # @api.model
    # def create(self, values):
    #     location_name       = values.get('name', False)
    #     location_code       = values.get('code', False)
    #     location_type_id    = values.get('location_type_id', False)
    #     location_values     = {
    #         'name'      : location_name or "(NoName)",
    #         'code'      : location_code or "(NoCode)",
    #         'type_id'   : location_type_id or False,
    #     }
    #     new_location = False
    #     location = super(lhm_project, self).create(values)
    #     if location:
    #         new_location = self.env['lhm.location'].create(location_values)
    #     if new_location:
    #         location.location_id = new_location.id
    #     return location
    #
    @api.multi
    def write(self, values):
        if 'name' in values and self.location_id:
            self.location_id.write({'code': values.get('name', False)})
        if 'code' in values and self.location_id:
            self.location_id.write({'name': values.get('code', False)})
        if 'location_type_id' in values and self.location_id:
            self.location_id.write({'type_id': values.get('location_type_id', False)})
        if 'active' in values and self.location_id:
            self.location_id.write({'active': values.get('active', False)})
        return super(lhm_project, self).write(values)

    @api.multi
    def unlink(self):
        for location in self:
            if location.location_id:
                location.location_id.unlink()
        location = super(lhm_project, self).unlink()
        return location

class lhm_project_line(models.Model):
    _name           = 'lhm.project.line'
    _description    = 'LHM Project Line'

    name            = fields.Char("Deskripsi", related="activity_id.name")
    activity_id     = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    vat             = fields.Float("PPN(%)")
    value           = fields.Float("Nilai")
    project_id      = fields.Many2one(comodel_name="lhm.project", string="Project", ondelete="cascade")
################################################### End Of Master Project ###################################################
############################################## Master Berat Janjang Rata-Rata ###############################################
class lhm_bjr(models.Model):
    _name           = 'lhm.bjr'
    _description    = 'LHM BJR'

    name        = fields.Char("Name", related="block_id.name", readonly=True)
    date        = fields.Date("Berlaku Mulai Tanggal", required=False)
    block_id    = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi", ondelete="restrict")
    value       = fields.Float('Penetapan BJR')
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active      = fields.Boolean("Active", default=True)
########################################### End Of Master Berat Janjang Rata-Rata ###########################################
#---------------------------------------------------------------------------------------------------------------------------#
#############################################################################################################################
#
#   This is for Transaction Models
#
#############################################################################################################################
#---------------------------------------------------------------------------------------------------------------------------#
###################################################### Transaction LHM ######################################################
class lhm_transaction(models.Model):
    _name           = 'lhm.transaction'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _order          = "date desc, kemandoran_code asc"
    _description    = 'Transaksi Laporan Harian Mandor'

    @api.model
    def _get_state(self):
        doc_id  = self.env['res.doc.type'].search([('code', '=', 'lhm')])[-1]
        if doc_id and doc_id.approval:
            state = [('draft', 'New'), ('in_progress', 'Progress'), ('confirmed', 'Confirmed'), ('done', 'Approved'), ('close', 'Close')]
        else:
            state = [('draft', 'New'), ('done', 'Progress'),('close', 'Close')]
        return state

    @api.depends('date','state')
    def _compute_account_period_id(self):
        for plantation_transaction in self:
            if plantation_transaction.date:
                period_id = self.env['account.period'].search([('date_start', '<=', plantation_transaction.date), ('date_stop', '>=', plantation_transaction.date), ('special','=',False)])
                if period_id:
                    plantation_transaction.account_period_id = period_id

    @api.one
    @api.depends('kemandoran_id','kemandoran_id.afdeling_id', 'kemandoran_id.division_id')
    def _compute_location(self):
        for loc in self:
            if loc.kemandoran_id.afdeling_id:
                loc.location = loc.kemandoran_id.afdeling_id.name
            elif loc.kemandoran_id.division_id:
                loc.location = loc.kemandoran_id.division_id.name
            else:
                loc.location = "NotDefined"

    @api.depends('user_id')
    def _compute_operating_unit_id(self):
        for plantation_transaction in self:
            if plantation_transaction.user_id:
                plantation_transaction.operating_unit_id = plantation_transaction.user_id.default_operating_unit_id

    def _default_doc_id(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'lhm')])[-1]
        return doc_id and doc_id.id or False

    name                = fields.Char("Nama", default="/")
    kemandoran_id       = fields.Many2one(comodel_name="hr.foreman", string="Kemandoran", ondelete="restrict", track_visibility='onchange')
    doc_type_id         = fields.Many2one(comodel_name="res.doc.type", string="Document Type", ondelete="restrict", track_visibility='onchange', default=_default_doc_id)
    approval            = fields.Boolean(string="Approval", related="doc_type_id.approval", readonly=True)
    date                = fields.Date("Tanggal", track_visibility='onchange')
    kemandoran_code     = fields.Char("Kode Kemandoran", related="kemandoran_id.code", readonly=True)
    mandor_id           = fields.Many2one(comodel_name="hr.employee", string="Mandor", ondelete="restrict", related="kemandoran_id.foreman_id", readonly=True, store=True)
    asisten_mandor_id   = fields.Many2one(comodel_name="hr.employee", string="Mandor 1", ondelete="restrict", related="kemandoran_id.foreman_id_1", readonly=True)
    kerani_id           = fields.Many2one(comodel_name="hr.employee", string="Kerani", ondelete="restrict", related="kemandoran_id.admin_id", readonly=True, store=True)
    location            = fields.Char("Afdeling/ Divisi", compute="_compute_location", readonly=True, store=True)
    nik_mandor          = fields.Char("NIK Mandor", related="kemandoran_id.nik_mandor", readonly=True)
    nik_mandor_1        = fields.Char("NIK Mandor 1", related="kemandoran_id.nik_mandor_1", readonly=True)
    nik_kerani          = fields.Char("NIK Kerani", related="kemandoran_id.nik_kerani", readonly=True)
    lhm_line_ids        = fields.One2many('lhm.transaction.line', 'lhm_id', string="Detail LHM", )
    process_line_ids    = fields.One2many('lhm.transaction.process.line', 'lhm_id', string="Detail Progress LHM", )
    material_line_ids   = fields.One2many('lhm.transaction.material.line', 'lhm_id', string="Detail Material LHM", )
    emp_out_ids         = fields.One2many('hr.employee.foreman.transfer', 'lhm_id', string="Detail Employee Transfer Out LHM", domain=[('type', '=', 'out')], readonly=1)
    emp_in_ids          = fields.One2many('hr.employee.foreman.transfer', 'lhm_id', string="Detail Employee Transfer In LHM", domain=[('type', '=', 'in')], readonly=1)
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    operating_unit_id   = fields.Many2one('operating.unit', string='Operating Unit', compute='_compute_operating_unit_id', readonly=True, store=True)
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", compute='_compute_account_period_id', readonly=True, store=True)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    note                = fields.Text("Catatan")
    state               = fields.Selection(selection=_get_state, string='Status',
                                    copy=False, default='draft', index=False, readonly=False, track_visibility='always',
                                    help="* New: Dokumen LHM baru.\n"
                                         "* Cancelled: LHM dibatalkan.\n"
                                         "* Progress: Proses Pengisian Progress.\n"
                                         "* Confirmed: LHM sudah diperiksa oleh Mandor.\n"
                                         "* Approved: LHM sudah disetujui oleh Asisten/Kepala Kebun. \n"
                                         "* Closed: LHM sudah diclosing. \n")
    invoice_id          = fields.Many2one('account.invoice', 'Payroll Invoice')
    pending_nab_link    = fields.Boolean('LHM belum sama dengan NAB', compute='_check_pending_nab_link', store=True)

    @api.multi
    @api.depends('process_line_ids.nab_line_ids', 'process_line_ids.nab_afkir_line_ids')
    def _check_pending_nab_link(self):
        for lhm in self:
            check = True
            for line in lhm.process_line_ids:
                if line.activity_id.is_panen:
                    nab_nilai = sum([x.qty_nab for x in line.nab_line_ids if x.lhm_nab_id.state!='draft']) \
                            + sum([x.qty for x in line.nab_afkir_line_ids if x.lhm_nab_afkir_id.state!='draft'])
                    if nab_nilai>=line.nilai:
                        check = False
            lhm.pending_nab_link = check

    @api.multi
    def get_material(self):
        move_obj            = self.env['stock.move']
        material_line_obj   = self.env['lhm.transaction.material.line']
        if self.material_line_ids:
            for material in self.material_line_ids:
                material.unlink()
        for progress in self.process_line_ids:
            if progress.activity_id and progress.location_id and progress.location_id.type_id.skb_declare == True:
                domain = [
                    ('date', '>=', str(self.account_period_id.date_start) + ' 00:00:01'), 
                    ('date', '<=', str(self.account_period_id.date_stop) + ' 23:59:59'), 
                    ('skb', '=', True), ('state', '=', 'done'), 
                    ('plantation_location_id', '=', progress.location_id.id), 
                    ('plantation_activity_id', '=', progress.activity_id.id), 
                    ('origin_returned_move_id', '=', False),
                    ('pending_material_allocation', '>', 0.0),
                    ]
                skb_ids     = move_obj.search(domain)
                for skb in skb_ids:
                    values_skb  = {
                        'name'              : skb.picking_id.bpb_number or '',
                        'date'              : self.date,
                        'product_id'        : skb.product_id.id,
                        'location_id'       : skb.plantation_location_id.id,
                        'activity_id'       : skb.plantation_activity_id.id,
                        'real_stock_qty'    : skb.product_uom_qty,
                        'stock_qty'         : skb.plantation_material_allocation,
                        'product_uom_id'    : skb.product_uom.id,
                        'move_id'           : skb.id,
                        'picking_id'        : skb.picking_id and skb.picking_id.id or False,
                        'lhm_id'            : self.id,
                        'progress_id'       : progress.id,
                    }
                    material_line_obj.create(values_skb)

    @api.multi
    def recalculate_plantation(self):
        all_plantation_ids  = self.env['lhm.transaction'].search([('account_period_id', '=', self.account_period_id.id)])
        for plantation in all_plantation_ids:
            for line in plantation.lhm_line_ids:
                if line.attendance_id and line.employee_id and line.min_wage_id:
                    if line.attendance_id:
                        line.valid      = True
                    if line.overtime_hour and line.overtime_hour > 0:
                        holiday         = False
                        overtime_data   = self.env['hr.overtime'].search([('hours', '=', line.overtime_hour)], limit=1)
                        holiday_data    = self.env['hr.holidays.public.line'].search([('date', '=', line.date)])
                        if holiday_data:
                            holiday     = True
                        if overtime_data and line.employee_id.type_id and line.employee_id.type_id.overtime_calc:
                            if holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                                line.overtime_value = (line.min_wage_id.umr_month / 173) * overtime_data.holiday
                            elif not holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                                line.overtime_value = (line.min_wage_id.umr_month / 173) * overtime_data.normal_day
                            else:
                                line.overtime_value = 0
                        if overtime_data and line.employee_id.type_id and not line.employee_id.type_id.overtime_calc:
                            if holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                                line.overtime_value = (line.min_wage_id.umr_month / 25) * float(float(3) / float(20)) * overtime_data.holiday
                            elif not holiday and overtime_data and line.min_wage_id.umr_month != 0.00:
                                line.overtime_value = (line.min_wage_id.umr_month / 25) * float(float(3) / float(20)) * overtime_data.normal_day
                            else:
                                line.overtime_value = 0

    @api.multi
    def reprogress_plantation(self):
        all_plantation_ids = self.env['lhm.transaction'].search([('state', 'in', ['in_progress','done']), ('account_period_id', '=', self.account_period_id.id)])
        for plantation in all_plantation_ids:
            plantation.run_progress()

    @api.onchange('date', 'kemandoran_id')
    def _onchange_kemandoran(self):
        other_ids = False
        if self.date and self.kemandoran_id:
            other_ids = self.env['lhm.transaction'].search([('id', '!=', self._origin.id), ('date', '=', self.date), ('kemandoran_id', '=', self.kemandoran_id.id)])
            if other_ids:
                self.date           = False
                self.kemandoran_id  = False
                return {
                    'value'     : {'lhm_line_ids': map(lambda x: (2, x), [x.id for x in self.lhm_line_ids])},
                    'warning'   : {'title': _('Kesalahan Input Data'),
                                   'message': _("Dokumen sudah ada: %s.") % other_ids[-1].name, },
                }
        if self.date and self.kemandoran_id and not other_ids:
            transfer_out_ids    = self.env['hr.employee.foreman.transfer'].search([('date', '=', self.date), ('type', '=', 'out'), ('kemandoran_to_id', '=', self.kemandoran_id.id), ('lhm_line_id', '=', False), ])
            transfer_in_ids     = self.env['hr.employee.foreman.transfer'].search([('date', '=', self.date), ('type', '=', 'in'), ('kemandoran_from_id', '=', self.kemandoran_id.id), ('lhm_line_id', '=', False)])
            other_out_attn      = self.env['hr.attendance.type'].search([('type', '=', 'out')], limit=1)
            other_in_attn       = self.env['hr.attendance.type'].search([('type', '=', 'in')], limit=1)
            emp_out_ids         = [x.employee_id.id for x in transfer_out_ids]
            list_employee       = []
            seq                 = 1
            for employee in self.kemandoran_id.employee_ids:
                min_wage    = False
                if employee and employee.basic_salary_type == 'employee':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_id', '=', employee.id), ('date_from', '<=', self.date), ('date_to', '>=', self.date)],limit=1)
                elif employee and employee.basic_salary_type == 'employee_type':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_type_id', '=', employee.type_id.id), ('date_from', '<=', self.date), ('date_to', '>=', self.date)], limit=1)
                if not min_wage:
                    return {
                        'value'     : {
                                        'lhm_line_ids'  : map(lambda x: (2, x), [x.id for x in self.lhm_line_ids]),
                                        'date'          : False,
                                        'kemandoran_id' : False,
                                    },
                        'warning'   : {
                                        'title': _('Kesalahan Input Data'),
                                        'message': _("UMR tidak ditemukan untuk range tanggal: %s.") % (self.date)
                                    },
                    }
                values          = {
                    'sequence'              : seq,
                    'date'                  : self.date or False,
                    'work_day'              : 0.0,
                    'non_work_day'          : 0.0,
                    'total_hke'             : 0.0,
                    'total_hkne'            : 0.0,
                    'min_wage_value_date'   : 0.0,
                    'work_result'           : 0.0,
                    'premi'                 : 0.0,
                    'overtime_value'        : 0.0,
                    'penalty'               : 0.0,
                    'name'                  : employee and employee.no_induk or False,
                    'employee_id'           : employee and employee.id or False,
                    'min_wage_id'           : min_wage and min_wage.id or False,
                    'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)),
                }
                if employee.id in emp_out_ids:
                    values.update({
                        'attendance_id' : other_out_attn and other_out_attn.id or False,
                        'transfer_id'   : self.env['hr.employee.foreman.transfer'].search([('date', '=', self.date), ('type', '=', 'out'), ('kemandoran_to_id', '=', self.kemandoran_id.id), ('lhm_line_id', '=', False), ('employee_id', '=', employee.id)], limit=1).id or False
                    })
                list_employee.append((0, 0, values))
                seq     += 1
            if transfer_in_ids:
                for transfer in transfer_in_ids:
                    values = {
                        'sequence'              : seq,
                        'date'                  : self.date or False,
                        'work_day'              : 0.0,
                        'non_work_day'          : 0.0,
                        'total_hke'             : 0.0,
                        'total_hkne'            : 0.0,
                        'min_wage_value_date'   : 0.0,
                        'work_result'           : 0.0,
                        'premi'                 : 0.0,
                        'overtime_value'        : 0.0,
                        'penalty'               : 0.0,
                        'name'                  : transfer and transfer.employee_id and transfer.employee_id.no_induk or False,
                        'employee_id'           : transfer and transfer.employee_id and transfer.employee_id.id or False,
                        'min_wage_id'           : min_wage and min_wage.id or False,
                        'min_wage_value'        : (min_wage.umr_month / (min_wage.work_day or 25)),
                        'attendance_id'         : other_in_attn and other_in_attn.id or False,
                        'transfer_id'           : transfer and transfer.id or False
                    }
                    list_employee.append((0, 0, values))
                    seq += 1
            self.lhm_line_ids = list_employee

    @api.multi
    def button_draft(self):
        if self.state in ['close']:
            raise ValidationError(_("Anda tidak dapat membatalkan dokumen dalam status Close!"))
        else:
            self.state      = 'draft'
            employee_ids    = []
            for line in self.lhm_line_ids:
                if line.attendance_id and line.employee_id and \
                        line.employee_id.type_id and line.employee_id.type_id.monthly_employee and line.employee_id.id not in employee_ids \
                        and line.valid and (line.work_day > 0 or line.non_work_day > 0):
                    employee_ids.append(line.employee_id.id)
            if employee_ids != []:
                self.check_all(self.account_period_id.date_start, self.account_period_id.date_stop, employee_ids)

            for line in self.lhm_line_ids:
                if line.attendance_id and line.employee_id and \
                    line.employee_id.type_id and line.employee_id.type_id.monthly_employee and line.employee_id and \
                    line.valid and (line.work_day > 0 or line.non_work_day > 0):
                    values = {
                        'total_hke'             : 0.0,
                        'total_hkne'            : 0.0,
                        'min_wage_value'        : line.min_wage_id.umr_month / line.min_wage_id.work_day,
                        'min_wage_value_date'   : 0.0,
                    }
                    line.write(values)
            return True
        return True

    @api.multi
    def button_confirm(self):
        self.state = 'confirmed'

    @api.multi
    def button_approve(self):
        self.state = 'done'

    @api.multi
    def button_reject(self):
        self.state = 'in_progress'

    @api.multi
    def check_all(self, date_start, date_stop, employe_ids):
        plantation_line_obj = self.env['lhm.transaction.line'].sudo()
        for employee_id in employe_ids:
            total_hke           = 0
            total_hkne          = 0
            total_hke_day       = 0
            total_hkne_day      = 0
            trans_valid         = []
            lhm_list            = []
            all_transaction_employee    = plantation_line_obj.search([('lhm_id.date', '>=', date_start), ('lhm_id.date', '<=', date_stop), ('employee_id', '=', employee_id)], order='date asc')
            for emp_transaction in all_transaction_employee:
                if emp_transaction.attendance_id and emp_transaction.employee_id.type_id.monthly_employee and (emp_transaction.lhm_id.state == 'done' or emp_transaction.lhm_id.state == 'in_progress'):
                    trans_valid.append(emp_transaction.id)
                    if emp_transaction.lhm_id.id not in lhm_list:
                        lhm_list.append(emp_transaction.lhm_id.id)
                if emp_transaction.work_day > 0 and emp_transaction.attendance_id and emp_transaction.attendance_id.type_hk == 'hke' and (emp_transaction.lhm_id.state == 'done' or emp_transaction.lhm_id.state == 'in_progress'):
                    total_hke += emp_transaction.work_day
                elif emp_transaction.non_work_day > 0 and emp_transaction.attendance_id and emp_transaction.attendance_id.type_hk == 'hkne' and emp_transaction.employee_id.type_id.monthly_employee and (emp_transaction.lhm_id.state == 'done' or emp_transaction.lhm_id.state == 'in_progress'):
                    total_hkne += emp_transaction.non_work_day
            for emp_transaction_write in plantation_line_obj.search([('id', 'in', trans_valid)], order='date asc'):
                if emp_transaction_write.work_day > 0 and emp_transaction_write.attendance_id and emp_transaction_write.attendance_id.type_hk == 'hke' and (emp_transaction_write.lhm_id.state == 'done' or emp_transaction_write.lhm_id.state == 'in_progress'):
                    total_hke_day += emp_transaction_write.work_day
                elif emp_transaction_write.non_work_day > 0 and emp_transaction_write.attendance_id and emp_transaction_write.attendance_id.type_hk == 'hkne' and emp_transaction_write.employee_id.type_id.monthly_employee and (emp_transaction_write.lhm_id.state == 'done' or emp_transaction_write.lhm_id.state == 'in_progress'):
                    total_hkne_day += emp_transaction_write.non_work_day
                if emp_transaction_write.attendance_id and (emp_transaction_write.non_work_day > 0 or emp_transaction_write.work_day > 0) and (emp_transaction_write.lhm_id.state == 'done' or emp_transaction_write.lhm_id.state == 'in_progress'):
                    values  = {
                        'total_hke'             : total_hke,
                        'total_hkne'            : total_hkne,
                        'min_wage_value'        : emp_transaction_write.min_wage_id.umr_month / (total_hke + total_hkne),
                        'min_wage_value_date'   : emp_transaction_write.min_wage_id.umr_month / (total_hke_day + total_hkne_day),
                        'min_wage_value_hkne'   : ((emp_transaction_write.min_wage_id.umr_month / (total_hke + total_hkne)) * total_hkne),
                    }
                    emp_transaction_write.write(values)
                else:
                    values = {
                        'total_hke'             : 0.0,
                        'total_hkne'            : 0.0,
                        'min_wage_value'        : emp_transaction_write.min_wage_id.umr_month / emp_transaction_write.min_wage_id.work_day,
                        'min_wage_value_date'   : 0.0,
                    }
                    emp_transaction_write.write(values)
            for lhm_reprogress in plantation_line_obj.search([('lhm_id', 'in', lhm_list)], order='date asc'):
                if (lhm_reprogress.lhm_id.state == 'done' or lhm_reprogress.lhm_id.state == 'in_progress'):
                    if lhm_reprogress.attendance_id and lhm_reprogress.employee_id and lhm_reprogress.employee_id.type_id and lhm_reprogress.employee_id.type_id.monthly_employee and \
                        (lhm_reprogress.non_work_day > 0 or lhm_reprogress.work_day > 0):
                        self.env.cr.execute("""
                            select ltl.activity_id,
                            ltl.location_id,
                            sum(ltl.work_day) as hk,
                            sum(ltl.work_day*ltl.min_wage_value)+sum(ltl.premi+ltl.overtime_value-ltl.penalty) as realisasi,
                            case when is_panen is TRUE then sum(ltl.work_result) else 0 end as nilai,
                            sum(ltl.premi+ltl.overtime_value-ltl.penalty) as premi,
                            sum(ltl.non_work_day) as hkne,
                            sum(ltl.min_wage_value_date)+sum(ltl.work_day*ltl.min_wage_value)+sum(ltl.premi+ltl.overtime_value-ltl.penalty)-sum(CASE WHEN ltl.min_wage_value_date > 0 THEN ltl.min_wage_value ELSE 0 END) as realisasi_date
                            from lhm_transaction_line ltl
                            left join lhm_activity la on ltl.activity_id = la.id
                            where ltl.activity_id is not NULL and lhm_id = %s group by ltl.activity_id, ltl.location_id, la.is_panen;
                            """, (lhm_reprogress.lhm_id.id,))
                        for progres in self.env.cr.fetchall():
                            progress_line   = self.env['lhm.transaction.process.line'].search([('activity_id', '=', progres[0]), ('location_id', '=', progres[1]), ('lhm_id', '=', lhm_reprogress.lhm_id.id)])
                            if progress_line:
                                new_lines = {
                                    'realization'       : progres[3],
                                    'realization_date'  : progres[7],
                                }
                                progress_line.write(new_lines)
        return True

    @api.multi
    def run_progress(self):
        lhm_progress_list   = []
        lhm_removed_list    = []
        sequence_number     = 1
        progress_line_obj   = self.env['lhm.transaction.process.line']
        if self.process_line_ids:
            for data in self.process_line_ids:
                lhm_progress_list.append(data.id)
        self.env.cr.execute("""
            select ltl.activity_id,
            ltl.location_id,
            sum(ltl.work_day) as hk,
            sum(ltl.work_day*ltl.min_wage_value)+sum(ltl.premi+ltl.overtime_value-ltl.penalty) as realisasi,
            case when is_panen is TRUE then sum(ltl.work_result) else 0 end as nilai,
            sum(ltl.premi+ltl.overtime_value-ltl.penalty) as premi,
            sum(ltl.non_work_day) as hkne,
            sum(ltl.min_wage_value_date)+sum(ltl.work_day*ltl.min_wage_value)+sum(ltl.premi+ltl.overtime_value-ltl.penalty)-sum(CASE WHEN ltl.min_wage_value_date > 0 THEN ltl.min_wage_value ELSE 0 END) as realisasi_date
            from lhm_transaction_line ltl
            left join lhm_activity la on ltl.activity_id = la.id
            where ltl.activity_id is not NULL and lhm_id = %s group by ltl.activity_id, ltl.location_id, la.is_panen;
            """, (self.id,))
        for progres in self.env.cr.fetchall():
            activity_data = self.env['lhm.activity'].search([('id', '=', progres[0])])
            if lhm_progress_list != []:
                progress_line   = progress_line_obj.search([('activity_id', '=', progres[0]), ('location_id', '=', progres[1]), ('lhm_id', '=', self.id)])
                if progress_line and len(progress_line) > 1:
                    raise ValidationError(_("Terjadi kesalahan (T.T), Error Code %s. \n"
                                            "Hubungi administrator untuk informasi lebih lanjut!"))
                if progress_line and len(progress_line) == 1:
                    if progress_line.nilai != progres[4] and progress_line.activity_id.is_panen:
                        progress_line.write({'nilai' : progres[4], 'updated': True,})
                    if progress_line.work_day != progres[2]:
                        progress_line.write({'work_day'  : progres[2], 'updated': True,})
                    if progress_line.non_work_day != progres[6]:
                        progress_line.write({'non_work_day'  : progres[6]})
                    if progress_line.realization != progres[3]:
                        progress_line.write({'realization'   : progres[3], 'updated': True,})
                    if progress_line.realization_date != progres[7]:
                        progress_line.write({'realization_date'   : progres[7]})
                    if progress_line.premi != progres[5]:
                        progress_line.write({'premi' : progres[5], 'updated': True,})
                    lhm_removed_list.append(progress_line.id)
                else:
                    new_lines = {
                        'sequence'          : sequence_number,
                        'date'              : self.date,
                        'activity_id'       : progres[0],
                        'location_id'       : progres[1],
                        'nilai'             : progres[4],
                        'uom_id'            : activity_data and activity_data.uom_id.id or False,
                        'nilai2'            : 0,
                        'uom2_id'           : activity_data and activity_data.uom2_id.id or False,
                        'work_day'          : progres[2],
                        'non_work_day'      : progres[6],
                        'realization'       : progres[3],
                        'realization_date'  : progres[7],
                        'premi'             : progres[5],
                        'lhm_id'            : self.id,
                    }
                    if new_lines:
                        self.env['lhm.transaction.process.line'].create(new_lines)
                        sequence_number     += 1
            elif lhm_progress_list == []:
                new_lines = {
                    'sequence'          : sequence_number,
                    'date'              : self.date,
                    'activity_id'       : progres[0],
                    'location_id'       : progres[1],
                    'nilai'             : progres[4],
                    'uom_id'            : activity_data and activity_data.uom_id.id or False,
                    'nilai2'            : 0,
                    'uom2_id'           : activity_data and activity_data.uom2_id.id or False,
                    'work_day'          : progres[2],
                    'non_work_day'      : progres[6],
                    'realization'       : progres[3],
                    'realization_date'  : progres[7],
                    'premi'             : progres[5],
                    'lhm_id'            : self.id,
                }
                if new_lines:
                    self.env['lhm.transaction.process.line'].create(new_lines)
                    sequence_number += 1
        if len(lhm_removed_list) != len(lhm_progress_list):
            to_remove_list = []
            if len(lhm_progress_list) > len(lhm_removed_list):
                to_remove_list = list(set(lhm_progress_list)^set(lhm_removed_list))
            for removed_progress in progress_line_obj.search([('id', 'in', to_remove_list)]):
                removed_progress.write({
                    'realization'       : 0.0,
                    'realization_date'  : 0.0,
                    'work_day'          : 0.0,
                    'premi'             : 0.0,
                    'deleted'           : True,
                })
        if False in [isinstance(x.attendance_id.id, bool) for x in self.lhm_line_ids]:
            self.name   = self.kemandoran_id.code + "/" + str(datetime.datetime.strptime(self.date, '%Y-%m-%d').strftime('%Y-%m-%d'))
            if self.doc_type_id.approval:
                self.state  = 'in_progress'
            else:
                self.state  = 'done'
        else:
            raise ValidationError(_("Minimal salah satu absensi di daftar karyawan harus terisi!"))
        for lhm_line in self.lhm_line_ids:
            if lhm_line.transfer_id:
                lhm_line.transfer_id.write({'name': self.name})

        employee_ids    = []
        for line in self.lhm_line_ids:
            if line.attendance_id and line.employee_id and \
                    line.employee_id.type_id and line.employee_id.type_id.monthly_employee and line.employee_id.id not in employee_ids \
                    and line.valid and (line.work_day > 0 or line.non_work_day > 0):
                employee_ids.append(line.employee_id.id)
        if employee_ids != []:
            self.check_all(self.account_period_id.date_start, self.account_period_id.date_stop, employee_ids)

    @api.multi
    def unlink(self):
        for transaction in self:
            if transaction.state != 'draft':
                raise UserError(_('Status dokumen LHM nomor %s dengan kemandoran %s adalah %s.\n'
                                  'Laporan Harian Mandor hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (transaction.name, transaction.kemandoran_id.name, transaction.state.title()))
            if transaction.lhm_line_ids:
                unlink_transfer = self.env['hr.employee.foreman.transfer'].search([('date', '=', transaction.date), '|', ('lhm_id', '=', transaction.id), ('other_lhm_id', '=', transaction.id)])
                if not unlink_transfer:
                    return super(lhm_transaction, self).unlink()
                    pass
                for transfer in unlink_transfer:
                    if (transfer.lhm_id and transfer.lhm_id.id) == transaction.id:
                        transfer.unlink()
                    elif (transfer.other_lhm_id and transfer.other_lhm_id.id) == transaction.id:
                        if transfer.lhm_line_id and transfer.lhm_id:
                            if transfer.lhm_id:
                                if transfer.lhm_id.state not in ['draft', 'in_progress']:
                                    raise UserError(_('Status dokumen LHM nomor %s dengan kemandoran %s adalah %s.\n'
                                                      'Hubungi kemandoran terkait untuk menghapus Daftar Karyawan') %
                                                    (transfer.lhm_id.name, transfer.lhm_id.kemandoran_id.name, transfer.lhm_id.state.title()))
                                else:
                                    new_values = {
                                        'attendance_id'         : False,
                                        'satuan_id'             : False,
                                        'activity_id'           : False,
                                        'location_id'           : False,
                                        'location_type_id'      : False,
                                        'valid'                 : False,
                                        'work_day'              : 0.0,
                                        'non_work_day'          : 0.0,
                                        'total_hke'             : 0.0,
                                        'total_hkne'            : 0.0,
                                        'min_wage_value_date'   : 0.0,
                                        'work_result'           : 0.0,
                                        'premi'                 : 0.0,
                                        'overtime_hour'         : 0.0,
                                        'overtime_value'        : 0.0,
                                        'penalty'               : 0.0,
                                    }
                                    transfer.lhm_line_id.write(new_values)
                                    transfer.unlink()
                            else:
                                transfer.unlink()
                        else:
                            transfer.unlink()
                    else:
                        pass
        transaction = super(lhm_transaction, self).unlink()
        return transaction

class lhm_transaction_line(models.Model):
    _name           = 'lhm.transaction.line'
    _description    = 'Detail Transaksi Laporan Harian Mandor'
    _order          = 'sequence'

    @api.multi
    @api.depends("location_type_id","location_id")
    def _get_doc_activity_ids(self):
        for object in self:
            activity_list   = []
            doc_id          = self.env['res.doc.type'].search([('code','=','lhm')])[-1]
            level_1         = self.env['lhm.activity'].search([('level','=',1)])[-1]
            avail_act       = self.env['lhm.activity'].search([('type_id','=',object.location_type_id.id)])
            if doc_id:
                for act in avail_act:
                    if doc_id.id in act.doc_ids.ids:
                        activity_list.append(act.id)
            if level_1:
                activity_list.append(level_1.id)
            if (object.location_type_id and object.location_type_id.project) and object.location_id:
                project_ids = self.env['lhm.project'].search([('location_id','=',object.location_id.id)])
                project_act = []
                avail       = []
                if level_1:
                    avail.append(level_1.id)
                for project in project_ids:
                    project_act += [x.activity_id.id for x in project.line_ids]
                if project_act != []:
                    for act_project in project_act:
                        if act_project in activity_list:
                            avail.append(act_project)
                if avail != []:
                    object.doc_activity_ids = [(6, 0, avail)]
            else:
                object.doc_activity_ids = [(6, 0, activity_list)]

    name                = fields.Char("NIK", related="employee_id.no_induk", readonly=True)
    date                = fields.Date("Date")
    sequence            = fields.Integer()
    employee_id         = fields.Many2one(comodel_name="hr.employee", string="Nama", ondelete="restrict")
    attendance_id       = fields.Many2one(comodel_name="hr.attendance.type", string="Absensi", ondelete="restrict")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    no_line             = fields.Boolean(string="Mandatory", related="location_type_id.no_line")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    satuan_id           = fields.Many2one(comodel_name="product.uom", string="Satuan", ondelete="restrict")
    transfer_id         = fields.Many2one(comodel_name="hr.employee.foreman.transfer", string="Transfer")
    doc_activity_ids    = fields.Many2many('lhm.activity', store=True, compute=_get_doc_activity_ids)
    work_day            = fields.Float("HK")
    non_work_day        = fields.Float("HKN")
    work_result         = fields.Float("Hasil")
    unit_price          = fields.Float("Tarif")
    premi               = fields.Float("Premi")
    overtime_hour       = fields.Integer("Jam Lembur")
    overtime_value      = fields.Float("Rupiah Lembur")
    penalty             = fields.Float("Penalty")
    kontanan            = fields.Boolean("Kontanan")
    progressive         = fields.Boolean("Progressive", related="employee_id.type_id.monthly_employee", readonly=True)
    valid               = fields.Boolean("Valid")
    panen               = fields.Boolean("Panen", related="activity_id.is_panen", readonly=True)
    overtime            = fields.Boolean("Overtime", related="employee_id.type_id.overtime_calc", readonly=True)
    attendance_type     = fields.Selection([('in', 'Masuk'), ('out', 'Keluar'), ('na', 'N/A'), ('kj', 'KJ')], string='Type', related="attendance_id.type", readonly=True)
    min_wage_id         = fields.Many2one(comodel_name="hr.minimum.wage", string="Upah Minimum", ondelete="restrict")
    total_hke           = fields.Float(string="Total HKE")
    total_hkne          = fields.Float(string="Total HKNE")
    min_wage_value      = fields.Float(string="Upah Minimum")
    min_wage_value_date = fields.Float(string="Upah Tanggal")
    min_wage_value_hkne = fields.Float(string="Upah HKNE")
    lhm_id              = fields.Many2one(comodel_name="lhm.transaction", string="LHM", ondelete="cascade")
    lhm_nab_ids         = fields.One2many('lhm.transaction.line.nab.line', 'lhm_line_id', 'LHM Detail')

    @api.onchange('attendance_id')
    def _onchange_attendance_id(self):
        non_work_day    = 0
        if self.attendance_id and self.attendance_id.type_hk == 'hkne' and \
                (self.employee_id.type_id.monthly_employee or self.employee_id.type_id.sku_employee \
                or self.employee_id.type_id.contract_employee):
            non_work_day    = 1
        if self.attendance_id:
            self.location_type_id   = False
            self.location_id        = False
            self.activity_id        = False
            self.satuan_id          = False
            self.work_day           = 0.0
            self.work_result        = 0.0
            self.premi              = 0.0
            self.overtime_hour      = 0.0
            self.overtime_value     = 0.0
            self.penalty            = 0.0
            self.valid              = True
            self.non_work_day       = non_work_day
        else:
            self.location_type_id   = False
            self.location_id        = False
            self.activity_id        = False
            self.satuan_id          = False
            self.work_day           = 0.0
            self.work_result        = 0.0
            self.premi              = 0.0
            self.overtime_hour      = 0.0
            self.overtime_value     = 0.0
            self.penalty            = 0.0
            self.valid              = False
            self.non_work_day       = 0.0

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id    = False
            self.activity_id    = False
            self.satuan_id      = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.activity_id    = False
            self.satuan_id      = False

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            self.satuan_id      = self.activity_id.uom_id and self.activity_id.uom_id.id or False

    @api.multi
    def _check_transfer_employee(self):
        for transfer in self:
            transfer_data   = transfer.transfer_id
            if transfer_data:
                if not transfer_data.lhm_id and not transfer_data.lhm_line_id:
                    transfer_data.write({
                        'name'          : self.lhm_id.name or '',
                        'lhm_id'        : self.lhm_id and self.lhm_id.id or False,
                        'lhm_line_id'   : self.id or False,
                    })
                    if transfer_data.other_lhm_line_id:
                        other_line_data = self.browse(transfer_data.other_lhm_line_id.id).transfer_id
                        if not other_line_data.other_lhm_id and not other_line_data.other_lhm_line_id:
                            other_line_data.write({
                                'other_lhm_id'      : self.lhm_id and self.lhm_id.id or False,
                                'other_lhm_line_id' : self.id or False,
                            })
        return True

    @api.multi
    def _check_work_day(self):
        for line in self:
            if line.attendance_id and line.attendance_id.special and line.attendance_id.type == 'kj':
                if line.work_day <= 0:
                    raise UserError(_('HK Wajib Diisi!'))

    @api.model
    def create(self, values):
        line    = super(lhm_transaction_line, self).create(values)
        line._check_transfer_employee()
        line._check_work_day()
        return line

    @api.multi
    def write(self, values):
        line    = super(lhm_transaction_line, self).write(values)
        self._check_work_day()
        return line

    @api.multi
    def unlink(self):
        for transaction_line in self:
            if transaction_line.transfer_id:
                unlink_transfer    = self.env['hr.employee.foreman.transfer'].search([('date', '=', self.date),'|',('lhm_line_id', '=', transaction_line.id),('other_lhm_line_id', '=', transaction_line.id)])
                for transfer in unlink_transfer:
                    if (transfer.lhm_line_id and transfer.lhm_line_id.id) == transaction_line.id:
                        transfer.unlink()
                    elif (transfer.other_lhm_line_id and transfer.other_lhm_line_id.id) == transaction_line.id:
                        if transfer.lhm_line_id and transfer.lhm_id:
                            if transfer.lhm_id:
                               if transfer.lhm_id.state not in ['draft','in_progress']:
                                   raise UserError(_('Status dokumen LHM nomor %s dengan kemandoran %s adalah %s.\n'
                                                     'Hubungi kemandoran terkait untuk menghapus Daftar Karyawan') %
                                                    (transfer.lhm_id.name, transfer.lhm_id.kemandoran_id.name, transfer.lhm_id.state.title()))
                               else:
                                   new_values = {
                                       'attendance_id'      : False,
                                       'satuan_id'          : False,
                                       'activity_id'        : False,
                                       'location_id'        : False,
                                       'location_type_id'   : False,
                                       'work_day'           : 0.0,
                                       'non_work_day'       : 0.0,
                                       'work_result'        : 0.0,
                                       'premi'              : 0.0,
                                       'overtime_hour'      : 0.0,
                                       'overtime_value'     : 0.0,
                                       'penalty'            : 0.0,
                                   }
                                   transfer.lhm_line_id.write(new_values)
                                   transfer.unlink()
                            else:
                                transfer.unlink()
                        else:
                            transfer.unlink()
                    else:
                        pass
        line = super(lhm_transaction_line, self).unlink()
        return line

    @api.onchange('overtime_hour')
    def _onchange_overtime_hour(self):
        if self.overtime_hour:
            holiday         = False
            overtime_data   = self.env['hr.overtime'].search([('hours','=',self.overtime_hour)], limit=1)
            holiday_data    = self.env['hr.holidays.public.line'].search([('date', '=', self.date)])
            if holiday_data:
                holiday = True
            if overtime_data and self.employee_id.type_id and self.employee_id.type_id.overtime_calc:
                if holiday and overtime_data and self.min_wage_id.umr_month != 0.00:
                    self.overtime_value = (self.min_wage_id.umr_month / 173) * overtime_data.holiday
                elif not holiday and overtime_data and self.min_wage_id.umr_month != 0.00:
                    self.overtime_value = (self.min_wage_id.umr_month / 173) * overtime_data.normal_day
                else:
                    self.overtime_value = 0
            if overtime_data and self.employee_id.type_id and not self.employee_id.type_id.overtime_calc:
                if holiday and overtime_data and self.min_wage_id.umr_month != 0.00:
                    self.overtime_value = (self.min_wage_id.umr_month / 25) * float(float(3)/float(20)) * overtime_data.holiday
                elif not holiday and overtime_data and self.min_wage_id.umr_month != 0.00:
                    self.overtime_value = (self.min_wage_id.umr_month / 25) * float(float(3)/float(20)) * overtime_data.normal_day
                else:
                    self.overtime_value = 0
        elif self.overtime_hour <= 0 :
            self.overtime_value = 0

    @api.onchange('work_day')
    def _onchange_work_day(self):
        if self.work_day:
            if self.attendance_id and self.attendance_id.type == 'na':
                self.work_day = 0
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("HK tidak boleh diisi jika Absensi: %s.") % self.attendance_id.code},
                }
            total_work_day  = 0
            if isinstance(self.id, int):
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('date', '=', self.date),
                    ('id', '!=', self.id)]
            else:
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('date', '=', self.date),
                    ('id', '!=', self._origin.id)]
            data_lhm_line   = self.search(domain)
            max_hk          = 1
            if not data_lhm_line:
                total_work_day  = 0
            else:
                for lhm_line in data_lhm_line:
                    total_work_day = total_work_day + lhm_line.work_day
            if (total_work_day + self.work_day) > max_hk:
                if (max_hk - total_work_day) < 0 and not data_lhm_line:
                    self.work_day = 1
                elif (max_hk - total_work_day) < 0 and data_lhm_line:
                    self.work_day = 0
                else:
                    self.work_day = max_hk - total_work_day
                return {
                        'warning': {'title': _('Kesalahan Input Data'), 'message': _("HK tidak boleh lebih dari: %s.") % max_hk },
                    }

    @api.multi
    @api.constrains('employee_id', 'attendance_id')
    def _check_attendance_id(self):
        for record in self:
            record._check_attendance_one()

    def _check_attendance_one(self):
        if self.attendance_id and self.employee_id and self.attendance_id.type in ['out','in']:
            if isinstance(self.id, int):
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('attendance_id', '=', self.attendance_id.id),
                    ('date', '=', self.date),
                    ('id', '!=', self.id)]
            else:
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('attendance_id', '=', self.attendance_id.id),
                    ('date', '=', self.date),
                    ('id', '!=', self._origin.id)]
            lhm_line    = self.search(domain)
            if lhm_line:
                raise UserError(_('Anda tidak dapat membuat daftar karyawan dengan nama %s dan absensi %s karena terjadi duplikasi data!') % (self.employee_id.name, self.attendance_id.code))
        return True


class lhm_transaction_process_line(models.Model):
    _name           = 'lhm.transaction.process.line'
    _description    = 'LHM Transaction Process Line'

    sequence            = fields.Integer()
    name                = fields.Char(related='activity_id.name', store=True, readonly=True)
    date                = fields.Date("Tanggal", )
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    nilai               = fields.Float('Nilai 1')
    uom_id              = fields.Many2one(comodel_name="product.uom", string="Satuan 1", ondelete="restrict")
    nilai2              = fields.Float('Nilai 2')
    uom2_id             = fields.Many2one(comodel_name="product.uom", string="Satuan 2", ondelete="restrict")
    work_day            = fields.Float('HK')
    non_work_day        = fields.Float('HKN')
    premi               = fields.Float('Premi')
    realization         = fields.Float('Realisasi')
    realization_date    = fields.Float(string="Realisasi Tanggal")
    deleted             = fields.Boolean('D')
    updated             = fields.Boolean('U')
    lhm_id              = fields.Many2one(comodel_name="lhm.transaction", string="LHM", ondelete="cascade")
    nab_line_ids        = fields.Many2many('lhm.nab.line', 'lhm_process_nab_line_rel', 'progress_id', 'nab_line_id', 'Nab Ref')
    nab_afkir_line_ids  = fields.Many2many('lhm.nab.afkir.line', 'lhm_process_nab_afkir_line_rel', 'progress_id', 'nab_afkir_line_id', 'Nab Afkir Ref')
    nab_nilai           = fields.Float('Nilai NAB', compute='_compute_qty_nab', store=True)

    @api.multi
    @api.depends('nab_line_ids', 'nab_afkir_line_ids')
    def _compute_qty_nab(self):
        for line in self:
            if line.activity_id.is_panen:
                line.nab_nilai = sum([x.qty_nab for x in line.nab_line_ids if x.lhm_nab_id.state!='draft']) \
                        + sum([x.qty for x in line.nab_afkir_line_ids if x.lhm_nab_afkir_id.state!='draft'])

class lhm_transaction_material_line(models.Model):
    _name           = 'lhm.transaction.material.line'
    _description    = 'LHM Transaction Material Line'

    name            = fields.Char(string="BPB", readonly=True)
    date            = fields.Date("Tanggal", )
    product_id      = fields.Many2one(comodel_name="product.product", string="Product", ondelete="restrict")
    activity_id     = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    activity_name   = fields.Char(related="activity_id.name", string="Name", ondelete="restrict")
    location_id     = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    real_stock_qty  = fields.Float('SKB Qty', digits=dp.get_precision('Product Unit of Measure'),)
    product_uom_id  = fields.Many2one(comodel_name="product.uom", string="UoM", ondelete="restrict")
    stock_qty       = fields.Float('Declared', digits=dp.get_precision('Product Unit of Measure'),)
    realization     = fields.Float('LHM Qty', digits=dp.get_precision('Product Unit of Measure'),)
    residual_qty    = fields.Float(compute='_get_residual', string='Residual', digits=dp.get_precision('Product Unit of Measure'),)
    # residual_qty    = fields.Float('Residual', digits=dp.get_precision('Product Unit of Measure'),)
    move_id         = fields.Many2one(comodel_name="stock.move", string="Stock Move", ondelete="restrict")
    picking_id      = fields.Many2one(comodel_name="stock.picking", string="Stock Picking", ondelete="restrict")
    progress_id     = fields.Many2one(comodel_name="lhm.transaction.process.line", string="Progress", ondelete="restrict")
    lhm_id          = fields.Many2one(comodel_name="lhm.transaction", string="LHM", ondelete="cascade")

    @api.depends('realization')
    def _get_residual(self):
        for line in self:
            residual = line.real_stock_qty - line.stock_qty - line.realization
            # if residual < 0:
            #     raise UserError(_('Realisasi Salah.\n'
            #                     'Realisasi tidak dapat melebihi Jumlah yg di SKB'))
            # else:
            #     line.residual_qty = residual
            line.residual_qty = residual


################################################## End Of Transaction LHM ###################################################
################################################## Transaction Buku Mesin ###################################################

class lhm_machine(models.Model):
    _name           = 'lhm.machine'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Buku Mesin'

    def _default_account_period_id(self):
        date        = time.strftime('%Y-%m-%d')
        period_id   = self.env['account.period'].search([('date_start', '<=', date),
                                                        ('date_stop', '>=', date),
                                                        ('special', '=', False)])
        period = False
        if period_id and len(period_id) > 1:
            period  = period_id[-1]
        elif period_id and len(period_id) == 1:
            period  = period_id
        return period and period.id or False

    @api.depends('user_id')
    def _compute_operating_unit_id(self):
        for plantation_transaction in self:
            if plantation_transaction.user_id:
                plantation_transaction.operating_unit_id = plantation_transaction.user_id.default_operating_unit_id

    def _default_doc_id(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bm')])[-1]
        return doc_id and doc_id.id or False

    def _default_state(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bm')])[-1]
        if doc_id and doc_id.approval:
            state = 'draft'
        else:
            state = 'confirmed'
        return state

    name                = fields.Char('Nama', required=False)
    machine_id          = fields.Many2one(comodel_name="lhm.utility", string="Mesin", ondelete="restrict", domain="[('type','=', 'ma')]")
    doc_type_id         = fields.Many2one(comodel_name="res.doc.type", string="Document Type", ondelete="restrict", track_visibility='onchange', default=_default_doc_id)
    approval            = fields.Boolean(string="Approval", related="doc_type_id.approval", readonly=True)
    machine_code        = fields.Char('Kode', readonly=True, related="machine_id.code")
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange', default=_default_account_period_id)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    uom_performance     = fields.Selection([('km', 'KM'), ('hm', 'HM')], string='Satuan', readonly=True, related="machine_id.uom_performance", store=True)
    line_ids            = fields.One2many(comodel_name='lhm.machine.line', inverse_name='lhm_machine_id', string="Detail Buku Mesin", )
    note                = fields.Text("Catatan")
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    operating_unit_id   = fields.Many2one('operating.unit', string='Operating Unit', compute='_compute_operating_unit_id', readonly=True, store=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state               = fields.Selection([
                            ('draft', 'New'), ('cancel', 'Cancelled'),
                            ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status',
                            copy=False, default=_default_state, index=True, readonly=True, track_visibility='onchange',
                            help="* New: Dokumen Baru.\n"
                                 "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                 "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                 "* Done: Dokumen Sudah Selesai Diproses. \n")

    @api.onchange('machine_id','account_period_id')
    def onchange_validate(self):
        if self.machine_id and self.account_period_id:
            other_ids = self.env['lhm.machine'].search([('id', '!=', self._origin.id), ('account_period_id', '=', self.account_period_id.id), ('machine_id', '=', self.machine_id.id)])
            if other_ids:
                self.account_period_id  = False
                self.machine_id         = False
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Dokumen sudah ada: %s.") % other_ids.name, },
                }

    @api.multi
    def unlink(self):
        for machine in self:
            if machine.state not in ['draft'] and self.doc_type_id.approval == True:
                raise UserError(_('Status dokumen Buku Mesin dengan nomor %s adalah %s.\n'
                                  'Buku Kendaraan hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (
                                    machine.name, machine.state.title()))
        machine = super(lhm_machine, self).unlink()
        return machine

    @api.multi
    def button_confirm(self):
        self.state = 'confirmed'

    @api.multi
    def button_draft(self):
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, values):
        machine     = self.env['lhm.utility'].search([('id', '=', values.get('machine_id'))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id'))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start,'%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start,'%Y-%m-%d').strftime('%Y')
            values['name']  = (machine.code or "") + "/" + year + "-" + month
        else:
            values['name']  = (machine.code or "") + "/"
        return super(lhm_machine, self).create(values)

    @api.multi
    def write(self, values):
        machine     = self.env['lhm.utility'].search([('id', '=', values.get('machine_id',self.machine_id.id))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id',self.account_period_id.id))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start,'%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start,'%Y-%m-%d').strftime('%Y')
            values['name']  = (machine.code or "") + "/" + year + "-" + month
        return super(lhm_machine, self).write(values)

class lhm_machine_line(models.Model):
    _name           = 'lhm.machine.line'
    _description    = 'LHM Machine Line'
    _order          = 'date, location_type_id, location_id, activity_id asc'

    @api.multi
    @api.depends("location_type_id","location_id")
    def _get_doc_activity_ids(self):
        for object in self:
            activity_list = []
            doc_id      = self.env['res.doc.type'].search([('code', '=', 'bm')])[-1]
            level_1     = self.env['lhm.activity'].search([('level', '=', 1)])[-1]
            avail_act   = self.env['lhm.activity'].search([('type_id', '=', object.location_type_id.id)])
            if doc_id:
                for act in avail_act:
                    if doc_id.id in act.doc_ids.ids:
                        activity_list.append(act.id)
            if level_1:
                activity_list.append(level_1.id)
            if (object.location_type_id and object.location_type_id.project) and object.location_id:
                project_ids = self.env['lhm.project'].search([('location_id', '=', object.location_id.id)])
                project_act = []
                avail = []
                if level_1:
                    avail.append(level_1.id)
                for project in project_ids:
                    project_act += [x.activity_id.id for x in project.line_ids]
                if project_act != []:
                    for act_project in project_act:
                        if act_project in activity_list:
                            avail.append(act_project)
                if avail != []:
                    object.doc_activity_ids = [(6, 0, avail)]
            else:
                object.doc_activity_ids = [(6, 0, activity_list)]

    name                = fields.Char("Nama", readonly=True, related="lhm_machine_id.name", store=True)
    date                = fields.Date("Tanggal", copy=False)
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    doc_activity_ids    = fields.Many2many('lhm.activity', store=True, compute=_get_doc_activity_ids)
    use_value           = fields.Float("Meter Pemakaian")
    use_hours           = fields.Float("Jam Kerja")
    lhm_machine_id      = fields.Many2one(comodel_name="lhm.machine", string="Buku Mesin", ondelete="cascade")

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id    = False
            self.activity_id    = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.activity_id    = False

    @api.multi
    @api.constrains('date')
    def _check_date_unique(self):
        for rec in self:
            rec._check_date_line()

    def _check_date_line(self):
        if not (self.date >= self.lhm_machine_id.account_period_id.date_start and self.date <= self.lhm_machine_id.account_period_id.date_stop):
            month = [item for item in BULAN_INDONESIA if item[0] == str(fields.Date.from_string(self.lhm_machine_id.account_period_id.date_start).month)][0][1]
            raise UserError(_('Tanggal %s pada Buku Mesin tidak dalam periode %s %s.\n'
                              'Ubah tanggal atau hapus baris di Daftar Buku Mesin') % (
                            self.date, month, str(fields.Date.from_string(self.lhm_machine_id.account_period_id.date_start).year)))
        # domain = [('date', '=', self.date)]
        # if self.search_count(domain) > 1:
        #     raise UserError(_('Tidak boleh ada tanggal yang sama.\n'
        #                       'Tanggal: %s') % self.date)
        return True
    @api.multi
    def copy_line(self):
        self.copy()
        return True
############################################## End Of Transaction Buku Mesin ################################################
################################################ Transaction Buku Kendaraan #################################################
class lhm_vehicle(models.Model):
    _name           = 'lhm.vehicle'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Buku Kendaraan'

    def _default_account_period_id(self):
        date        = time.strftime('%Y-%m-%d')
        period_id   = self.env['account.period'].search([('date_start', '<=', date),
                                                         ('date_stop', '>=', date),
                                                         ('special', '=', False)])
        period      = False
        if period_id and len(period_id) > 1:
            period  = period_id[-1]
        elif period_id and len(period_id) == 1:
            period  = period_id
        return period and period.id or False

    @api.depends('user_id')
    def _compute_operating_unit_id(self):
        for plantation_transaction in self:
            if plantation_transaction.user_id:
                plantation_transaction.operating_unit_id = plantation_transaction.user_id.default_operating_unit_id

    def _default_doc_id(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bk')])[-1]
        return doc_id and doc_id.id or False

    def _default_state(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bk')])[-1]
        if doc_id and doc_id.approval:
            state = 'draft'
        else:
            state = 'confirmed'
        return state


    name                = fields.Char('Nama', required=False)
    vehicle_id          = fields.Many2one(comodel_name="lhm.utility", string="Kendaraan", ondelete="restrict", domain="[('type','=', 'vh')]")
    doc_type_id         = fields.Many2one(comodel_name="res.doc.type", string="Document Type", ondelete="restrict", track_visibility='onchange', default=_default_doc_id)
    approval            = fields.Boolean(string="Approval", related="doc_type_id.approval", readonly=1)
    vehicle_code        = fields.Char('Kode', readonly=True, related="vehicle_id.code", store=True)
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange', default=_default_account_period_id)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    reg_number          = fields.Char("Nomor Polisi", readonly=True, related="vehicle_id.reg_number", store=True)
    uom_performance     = fields.Selection([('km', 'KM'), ('hm', 'HM')], string='Satuan', readonly=True, related="vehicle_id.uom_performance", store=True)
    operating_unit_id   = fields.Many2one('operating.unit', string='Operating Unit', compute='_compute_operating_unit_id', readonly=True, store=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids            = fields.One2many(comodel_name='lhm.vehicle.line', inverse_name='lhm_vehicle_id', string="Detail Buku Kendaraan", )
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    state               = fields.Selection([
                                ('draft', 'New'), ('cancel', 'Cancelled'),
                                ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status',
                                copy=False, default=_default_state, index=True, readonly=True,
                                help="* New: Dokumen Baru.\n"
                                     "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                     "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                     "* Done: Dokumen Sudah Selesai Diproses. \n")

    @api.onchange('vehicle_id','account_period_id')
    def onchange_validate(self):
        if self.vehicle_id and self.account_period_id:
            other_ids = self.env['lhm.vehicle'].search([('id', '!=', self._origin.id), ('account_period_id', '=', self.account_period_id.id), ('vehicle_id', '=', self.vehicle_id.id)])
            if other_ids:
                self.account_period_id  = False
                self.vehicle_id         = False
                return {
                    'warning'   : {'title': _('Kesalahan Input Data'),
                                    'message': _("Dokumen sudah ada: %s.") % other_ids[-1].name, },
                }

    @api.multi
    def unlink(self):
        for vehicle in self:
            if vehicle.state not in ['draft'] and self.doc_type_id.approval == True:
                raise UserError(_('Status dokumen Buku Kendaraan dengan nomor %s adalah %s.\n'
                                  'Buku Kendaraan hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (vehicle.name, vehicle.state.title()))
        vehicle = super(lhm_vehicle, self).unlink()
        return vehicle

    @api.multi
    def button_confirm(self):
        self.state = 'confirmed'

    @api.multi
    def button_draft(self):
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, values):
        vehicle     = self.env['lhm.utility'].search([('id', '=', values.get('vehicle_id'))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id'))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (vehicle.code or "") + "/" + year + "-" + month
        else:
            values['name'] = (vehicle.code or "") + "/"
        return super(lhm_vehicle, self).create(values)

    @api.multi
    def write(self, values):
        vehicle     = self.env['lhm.utility'].search([('id', '=', values.get('vehicle_id', self.vehicle_id.id))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id', self.account_period_id.id))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (vehicle.code or "") + "/" + year + "-" + month
        return super(lhm_vehicle, self).write(values)

class lhm_vehicle_line(models.Model):
    _name           = 'lhm.vehicle.line'
    _description    = 'LHM Vehicle Line'

    @api.multi
    @api.depends("start_value", "end_value")
    def  _compute_difference(self):
        for diff in self:
            diff.difference_value = diff.end_value - diff.start_value

    @api.multi
    @api.depends("location_type_id","location_id")
    def _get_doc_activity_ids(self):
        for object in self:
            activity_list = []
            doc_id      = self.env['res.doc.type'].search([('code', '=', 'bk')])[-1]
            level_1     = self.env['lhm.activity'].search([('level', '=', 1)])[-1]
            avail_act   = self.env['lhm.activity'].search([('type_id', '=', object.location_type_id.id)])
            if doc_id:
                for act in avail_act:
                    if doc_id.id in act.doc_ids.ids:
                        activity_list.append(act.id)
            if level_1:
                activity_list.append(level_1.id)
            if (object.location_type_id and object.location_type_id.project) and object.location_id:
                project_ids = self.env['lhm.project'].search([('location_id', '=', object.location_id.id)])
                project_act = []
                avail = []
                if level_1:
                    avail.append(level_1.id)
                for project in project_ids:
                    project_act += [x.activity_id.id for x in project.line_ids]
                if project_act != []:
                    for act_project in project_act:
                        if act_project in activity_list:
                            avail.append(act_project)
                if avail != []:
                    object.doc_activity_ids = [(6, 0, avail)]
            else:
                object.doc_activity_ids = [(6, 0, activity_list)]

    @api.multi
    @api.depends("activity_id")
    def _get_charge_activity_ids(self):
        for line in self:
            if line.activity_id and line.activity_id.charge_ids:
                line.filter_charge_ids = [(6, 0, [x.id for x in line.activity_id.charge_ids])]
            else:
                line.filter_charge_ids = []

    name                = fields.Char("Nama", readonly=True, related="lhm_vehicle_id.name", store=True)
    date                = fields.Date("Tanggal", )
    use_hours           = fields.Float("Jam Kerja")
    start_value         = fields.Float("km/hm Berangkat")
    end_value           = fields.Float("km/hm Kembali")
    difference_value    = fields.Float("km/hm Terpakai", compute="_compute_difference", store=True)
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    doc_activity_ids    = fields.Many2many('lhm.activity', store=True, compute=_get_doc_activity_ids)
    sub_activity_id     = fields.Many2one(comodel_name="lhm.activity", string="Sub Aktivitas", ondelete="restrict")
    performance1        = fields.Float("Prestasi")
    uom_performance1_id = fields.Many2one(comodel_name="product.uom", string="Satuan 1", ondelete="restrict")
    performance2        = fields.Float("Prestasi 2")
    uom_performance2_id = fields.Many2one(comodel_name="product.uom", string="Satuan 2", ondelete="restrict")
    filter_charge_ids   = fields.Many2many('lhm.charge.type', store=True, compute=_get_charge_activity_ids)
    charge_id           = fields.Many2one(comodel_name="lhm.charge.type", string="Muatan", ondelete="restrict")
    value_charge        = fields.Float("Vol. Muatan")
    uom_charge_id       = fields.Many2one(comodel_name="product.uom", string="Satuan Muatan", ondelete="restrict")
    lhm_vehicle_id      = fields.Many2one(comodel_name="lhm.vehicle", string="Buku Kendaraan", ondelete="cascade")

    @api.model
    def default_get(self, default_fields):
        #default_get should only do the following:
        #   -propose the next amount in start_value in order to reduce user input mistake
        lhm_vehicle_obj = self.env['lhm.vehicle']
        period_obj = self.env['account.period']
        context = self._context

        data = super(lhm_vehicle_line, self).default_get(default_fields)
        if not context.get('line_ids') and context.get('vehicle_id') and context.get('period_id'):
            period = period_obj.browse(context.get('period_id'))
            prev_lhm = self.search([('lhm_vehicle_id.vehicle_id', '=', context['vehicle_id']),
                                                       ('lhm_vehicle_id.state', 'in', ['done','confirmed']),
                                                       ('date','<=',period.date_start)],
                                                       order='date desc', limit=1)
            if prev_lhm:
                last_end_value = prev_lhm.end_value
                default_date = period.date_start

                data['start_value'] = last_end_value
                data['date'] = default_date
        elif context.get('line_ids'):
            line_dict = lhm_vehicle_obj.resolve_2many_commands('line_ids', context.get('line_ids'))
            last_end_value = max([x['end_value'] for x in line_dict])
            default_date = max([x['date'] for x in line_dict])

            data['start_value'] = last_end_value
            data['date'] = default_date
        return data

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            self.uom_performance1_id = self.activity_id.uom_id and self.activity_id.uom_id.id or False
            self.uom_performance2_id = self.activity_id.uom2_id and self.activity_id.uom2_id.id or False
            self.charge_id = self.activity_id.charge_ids and  self.activity_id.charge_ids[0].id or False
            self.uom_charge_id = self.activity_id.charge_ids and  self.activity_id.charge_ids[0].uom_id.id or False

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id        = False
            self.activity_id        = False
            self.sub_activity_id    = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.activity_id        = False
            self.sub_activity_id    = False

    @api.multi
    @api.constrains('date')
    def _check_date_unique(self):
        for rec in self:
            rec._check_date_line()

    def _check_date_line(self):
        if not (self.date >= self.lhm_vehicle_id.account_period_id.date_start and self.date <= self.lhm_vehicle_id.account_period_id.date_stop):
            month = [item for item in BULAN_INDONESIA if item[0] == str(fields.Date.from_string(self.lhm_vehicle_id.account_period_id.date_start).month)][0][1]
            raise UserError(_('Tanggal %s pada Buku Kendaraan tidak dalam periode %s %s.\n'
                              'Ubah tanggal atau hapus baris di Daftar Buku Kendaraan') % (
                                self.date, month, str(fields.Date.from_string(self.lhm_vehicle_id.account_period_id.date_start).year)))
        # domain = [('date', '=', self.date)]
        # if self.search_count(domain) > 1:
        #     raise UserError(_('Tidak boleh ada tanggal yang sama.\n'
        #                       'Tanggal: %s') % self.date)
        return True
############################################ End Of Transaction Buku Kendaraan ##############################################
################################################ Transaction Buku Workshop ##################################################
class lhm_workshop(models.Model):
    _name           = 'lhm.workshop'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Buku Workshop'

    def _default_account_period_id(self):
        date        = time.strftime('%Y-%m-%d')
        period_id   = self.env['account.period'].search([('date_start', '<=', date),
                                                       ('date_stop', '>=', date),
                                                       ('special', '=', False)])
        period = False
        if period_id and len(period_id) > 1:
            period = period_id[-1]
        elif period_id and len(period_id) == 1:
            period = period_id
        return period and period.id or False

    @api.depends('user_id')
    def _compute_operating_unit_id(self):
        for plantation_transaction in self:
            if plantation_transaction.user_id:
                plantation_transaction.operating_unit_id = plantation_transaction.user_id.default_operating_unit_id

    def _default_doc_id(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bw')])[-1]
        return doc_id and doc_id.id or False

    def _default_state(self):
        doc_id = self.env['res.doc.type'].search([('code', '=', 'bw')])[-1]
        if doc_id and doc_id.approval:
            state = 'draft'
        else:
            state = 'confirmed'
        return state

    name                = fields.Char('Nama', required=False)
    workshop_id         = fields.Many2one(comodel_name="lhm.utility", string="Workshop", ondelete="restrict", domain="[('type','=', 'ws')]")
    workshop_code       = fields.Char('Kode', readonly=True, related="workshop_id.code", store=True)
    doc_type_id         = fields.Many2one(comodel_name="res.doc.type", string="Document Type", ondelete="restrict", track_visibility='onchange', default=_default_doc_id)
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange', default=_default_account_period_id)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    approval            = fields.Boolean(string="Approval", related="doc_type_id.approval", readonly=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    operating_unit_id   = fields.Many2one('operating.unit', string='Operating Unit', compute='_compute_operating_unit_id', readonly=True, store=True)
    line_ids            = fields.One2many(comodel_name='lhm.workshop.line', inverse_name='lhm_workshop_id', string="Detail Buku Workshop", )
    note                = fields.Text("Catatan")
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    state               = fields.Selection([
                            ('draft', 'New'), ('cancel', 'Cancelled'),
                            ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status',
                            copy=False, default=_default_state, index=True, readonly=True,
                            help="* New: Dokumen Baru.\n"
                                 "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                 "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                 "* Done: Dokumen Sudah Selesai Diproses. \n")

    @api.onchange('workshop_id','account_period_id')
    def onchange_validate(self):
        if self.workshop_id and self.account_period_id:
            other_ids = self.env['lhm.workshop'].search([('id', '!=', self._origin.id), ('account_period_id', '=', self.account_period_id.id), ('workshop_id', '=', self.workshop_id.id)])
            if other_ids:
                self.account_period_id  = False
                self.workshop_id        = False
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Dokumen sudah ada: %s.") % other_ids.name, },
                }

    @api.multi
    def unlink(self):
        for workshop in self:
            if workshop.state not in ['draft'] and self.doc_type_id.approval == True:
                raise UserError(_('Status dokumen Buku Workshop dengan nomor %s adalah %s.\n'
                                  'Buku Workshop hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (
                                   workshop.name, workshop.state.title()))
        workshop = super(lhm_workshop, self).unlink()
        return workshop

    @api.multi
    def button_confirm(self):
        self.state = 'confirmed'

    @api.multi
    def button_draft(self):
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, values):
        workshop    = self.env['lhm.utility'].search([('id', '=', values.get('workshop_id'))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id'))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (workshop.code or "") + "/" + year + "-" + month
        else:
            values['name']  = (workshop.code or "") + "/"
        return super(lhm_workshop, self).create(values)

    @api.multi
    def write(self, values):
        workshop    = self.env['lhm.utility'].search([('id', '=', values.get('workshop_id', self.workshop_id.id))])
        period_id   = self.env['account.period'].search([('id', '=', values.get('account_period_id', self.account_period_id.id))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (workshop.code or "") + "/" + year + "-" + month
        return super(lhm_workshop, self).write(values)

class lhm_workshop_line(models.Model):
    _name           = 'lhm.workshop.line'
    _description    = 'LHM Workshop Line'

    @api.multi
    @api.depends("location_type_id","location_id")
    def _get_doc_activity_ids(self):
        for object in self:
            activity_list = []
            doc_id      = self.env['res.doc.type'].search([('code', '=', 'bw')])[-1]
            level_1     = self.env['lhm.activity'].search([('level', '=', 1)])[-1]
            avail_act   = self.env['lhm.activity'].search([('type_id', '=', object.location_type_id.id)])
            if doc_id:
                for act in avail_act:
                    if doc_id.id in act.doc_ids.ids:
                        activity_list.append(act.id)
            if level_1:
                activity_list.append(level_1.id)
            if (object.location_type_id and object.location_type_id.project) and object.location_id:
                project_ids = self.env['lhm.project'].search([('location_id', '=', object.location_id.id)])
                project_act = []
                avail = []
                if level_1:
                    avail.append(level_1.id)
                for project in project_ids:
                    project_act += [x.activity_id.id for x in project.line_ids]
                if project_act != []:
                    for act_project in project_act:
                        if act_project in activity_list:
                            avail.append(act_project)
                if avail != []:
                    object.doc_activity_ids = [(6, 0, avail)]
            else:
                object.doc_activity_ids = [(6, 0, activity_list)]

    name                = fields.Char("Nama", readonly=True, related="lhm_workshop_id.name", store=True)
    date                = fields.Date("Tanggal", )
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    doc_activity_ids    = fields.Many2many('lhm.activity', store=True, compute=_get_doc_activity_ids)
    use_hours           = fields.Float("Jam Kerja")
    lhm_workshop_id     = fields.Many2one(comodel_name="lhm.workshop", string="Buku Workshop", ondelete="cascade")

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id    = False
            self.activity_id    = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.activity_id    = False

    @api.multi
    @api.constrains('date','location_id','activity_id', 'lhm_workshop_id')
    def _check_date_unique(self):
        for rec in self:
            rec._check_date_line()

    def _check_date_line(self):
        if not (self.date >= self.lhm_workshop_id.account_period_id.date_start and self.date <= self.lhm_workshop_id.account_period_id.date_stop):
            month = [item for item in BULAN_INDONESIA if item[0] == str(fields.Date.from_string(self.lhm_workshop_id.account_period_id.date_start).month)][0][1]
            raise UserError(_('Tanggal %s pada Buku Workshop tidak dalam periode %s %s.\n'
                              'Ubah tanggal atau hapus baris di Daftar Buku Workshop') % (
                            self.date, month, str(fields.Date.from_string(self.lhm_workshop_id.account_period_id.date_start).year)))
        domain = []
        total_domain = 0
        if self.date:
            domain.append(('date', '=', self.date))
            total_domain += 1
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
            total_domain += 1
        if self.activity_id:
            domain.append(('activity_id', '=', self.activity_id.id))
            total_domain += 1
        if total_domain == 3 and self.search_count(domain) > 1:
            raise UserError(_('Terjadi Duplikasi Data!!!!.\n'
                              'Tanggal          : %s.\n'
                              'Kode Lokasi      : %s.\n'
                              'Kode Aktivitas   : %s.\n'
                              'Ganti salah satu detail atau hapus baris yang sama') % (self.date, self.location_id.code, self.activity_id.code))
        return True
############################################ End Of Transaction Buku Workshop ###############################################
############################################### Transaction Buku Kontraktor #################################################
class lhm_contractor(models.Model):
    _name           = 'lhm.contractor'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Buku Kontraktor'

    def _default_account_period_id(self):
        date = time.strftime('%Y-%m-%d')
        period_id = self.env['account.period'].search([('date_start', '<=', date),
                                                       ('date_stop', '>=', date),
                                                       ('special', '=', False)])
        period = False
        if period_id and len(period_id) > 1:
            period = period_id[-1]
        elif period_id and len(period_id) == 1:
            period = period_id
        return period and period.id or False

    @api.depends('user_id')
    def _compute_operating_unit_id(self):
        for plantation_transaction in self:
            if plantation_transaction.user_id:
                plantation_transaction.operating_unit_id = plantation_transaction.user_id.default_operating_unit_id

    def _default_doc_id(self):
        if self._context.get('default_type',self.type) == 'vendor':
            doc_id = self.env['res.doc.type'].search([('code', '=', 'bkt')])[-1]
        else:
            doc_id = self.env['res.doc.type'].search([('code', '=', 'bkta')])[-1]
        return doc_id and doc_id.id or False

    def _default_state(self):
        if self._context.get('default_type',self.type) == 'vendor':
            doc_id = self.env['res.doc.type'].search([('code', '=', 'bkt')])[-1]
        else:
            doc_id = self.env['res.doc.type'].search([('code', '=', 'bkta')])[-1]
        if doc_id and doc_id.approval:
            state = 'draft'
        else:
            state = 'confirmed'
        return state


    name                = fields.Char('Nama', required=False)
    type                = fields.Selection([('vehicle','Alat'),('vendor','Vendor')], string='Type', index=False, readonly=True)
    supplier_id         = fields.Many2one(comodel_name="res.partner", string="Kontraktor", ondelete="restrict")
    supplier_code       = fields.Char('Kode', readonly=True, related="supplier_id.ref")
    doc_type_id         = fields.Many2one(comodel_name="res.doc.type", string="Document Type", ondelete="restrict", track_visibility='onchange', default=_default_doc_id)
    approval            = fields.Boolean(string="Approval", related="doc_type_id.approval", readonly=True)
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange', default=_default_account_period_id)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    operating_unit_id   = fields.Many2one('operating.unit', string='Operating Unit', compute='_compute_operating_unit_id', readonly=True, store=True)  #
    date_start          = fields.Date("Tanggal Pembayaran Mulai")
    date_end            = fields.Date("Tanggal Pembayaran Selesai")
    contractor_vehicle  = fields.Boolean(string="Vehicle")
    total_type          = fields.Selection([('used', 'HM/KM Terpakai'), ('result', 'Hasil Kerja')], string='Kalkulasi')
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids            = fields.One2many('lhm.contractor.line', 'contractor_id', string="Detail Kontraktor", )
    line_vehicle_ids    = fields.One2many('lhm.contractor.vehicle.line', 'contractor_id', string="Detail Kontraktor Alat", )
    payment_type        = fields.Selection([('payment0', 'Pembayaran 1 Bulan Penuh'),('payment1','Pembayaran Ke-1'),('payment2','Pembayaran Ke-2')], string='Pembayaran', index=False, readonly=False)
    user_id             = fields.Many2one('res.users', string='Penanggung Jawab', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    note                = fields.Text('Catatan')
    state               = fields.Selection([
                            ('draft', 'New'), ('cancel', 'Cancelled'),
                            ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status',
                            copy=False, default=_default_state, index=True, readonly=True,
                            help="* New: Dokumen Baru.\n"
                                 "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                 "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                 "* Done: Dokumen Sudah Selesai Diproses. \n")
    invoice_id          = fields.Many2one('account.invoice', 'Invoice')
    move_id             = fields.Many2one('account.move', 'Journal Entry')
    amount_total        = fields.Float(compute='_compute_total', string='Total')
    material_line_ids   = fields.One2many('lhm.contractor.material.line', 'contractor_id', string="Detail Material")

    @api.depends('line_ids.unit_price', 'line_ids.nilai', 'line_vehicle_ids.unit_price', 'line_vehicle_ids.nilai')
    def _compute_total(self):
        for rec in self:
            amount_total = 0.0
            for line in rec.line_ids:
                amount_total += line.total
            for line in rec.line_vehicle_ids:
                amount_total += line.total
            rec.amount_total = amount_total
                
    @api.multi
    @api.constrains('date_start', 'date_end', 'contractor_vehicle', 'type')
    def _check_date_unique(self):
        for rec in self:
            # records = self.search([('supplier_id','=',rec.supplier_id.id),('id','!=',rec.id),('date_start','=',rec.date_start),('date_end','=',rec.date_end),('contractor_vehicle','=',rec.contractor_vehicle), ('type','=',rec.type)])
            if rec.contractor_vehicle:
                records = self.env['lhm.contractor.line'].search([('contractor_id.supplier_id','=',rec.supplier_id.id),
                    ('contractor_id','!=',rec.id),
                    ('date','>=',rec.date_start),('date','<=',rec.date_end),
                    ('contractor_id.contractor_vehicle','=',rec.contractor_vehicle), 
                    ('contractor_id.type','=',rec.type)])
            else:
                records = self.env['lhm.contractor.vehicle.line'].search([('contractor_id.supplier_id','=',rec.supplier_id.id),
                    ('contractor_id','!=',rec.id),
                    ('date','>=',rec.date_start),('date','<=',rec.date_end),
                    ('contractor_id.contractor_vehicle','=',rec.contractor_vehicle), 
                    ('contractor_id.type','=',rec.type)])

            if records:
                raise UserError(_('Buku Kontraktor sudah pernah dibuat untuk periode %s.')%rec.account_period_id.name)

    # @api.onchange('date_start', 'date_end', 'supplier_id', 'contractor_vehicle', 'payment_type')
    # def onchange_validate(self):
    #     if not self.date_start or not self.date_end:
    #         return {}
    #     if self.payment_type

    #     if self.date_start > self.date_end:
    #         self.date_end = self.date_start
    #         return {
    #                 'warning': {'title': _('Kesalahan Input Data'),
    #                             'message': _("Tanggal Berakhir Harus Lebih Besar dari Tanggal Mulai")},
    #             }

    #     # domain = [('id', '!=', self._origin.id), ('date_from', '>=', self.date_from)]
    #     domain = [('id', '!=', self._origin.id)]
    #     if self.activity_id:
    #         domain.append(('activity_id', '=', self.activity_id.id))
    #     else:
    #         domain.append(('activity_id', '=', False))

    #     if self.basic_salary_type and self.basic_salary_type=='employee' and self.employee_id:
    #         self.employee_type_id = False
    #         domain.append(('employee_id', '=', self.employee_id.id))
    #     else:
    #         domain.append(('employee_id', '=', False))
        
    #     if self.basic_salary_type and self.basic_salary_type=='employee_type' and self.employee_type_id:
    #         self.employee_id = False
    #         domain.append(('employee_type_id', '=', self.employee_type_id.id))
    #     else:
    #         domain.append(('employee_type_id', '=', False))

    #     # Validasi UMR yg sama jika tanggal berakhir-nya sudah didefinisikan ditempat lain
    #     check = self.env['hr.minimum.wage'].search(domain+[('date_to','>=',self.date_from)], order="date_to asc")
    #     if check:
    #         self.date_from = False
    #         self.date_to = False
    #         return {
    #                 'warning': {'title': _('Invalid Data Input'),
    #                     'message': _("UMR ini sudah didefinisikan pada %s dengan durasi antara %s s.d %s \n\
    #                     Silahkan diubah terlebih dahulu untuk membuat durasi UMR baru")% \
    #                     (check[-1].name, check[-1].date_from, check[-1].date_to)
    #                     },
    #                 }

    @api.onchange('supplier_id','account_period_id','payment_type','contractor_vehicle')
    def onchange_validate(self):
        if self.supplier_id and self.account_period_id and self.type:
            other_ids = self.env['lhm.contractor'].search([('id', '!=', self._origin.id), ('account_period_id', '=', self.account_period_id.id), ('supplier_id', '=', self.supplier_id.id), ('payment_type', '=', self.payment_type), ('type','=',self.type), ('contractor_vehicle','=',self.contractor_vehicle)])
            # other_ids = self.env['lhm.contractor'].search([('id', '!=', self._origin.id), 
            #     ('account_period_id', '=', self.account_period_id.id), 
            #     ('supplier_id', '=', self.supplier_id.id), 
            #     ('payment_type', '=', self.payment_type), 
            #     ('type','=',self.type), 
            #     ('contractor_vehicle','=',self.contractor_vehicle)])
            if other_ids:
                self.account_period_id  = False
                self.supplier_id        = False
                self.date_start         = False
                self.date_end           = False
                return {
                    'warning': {'title': _('Kesalahan Input Data'),
                                'message': _("Dokumen sudah ada: %s.") % other_ids.name, },
                }
            if self.payment_type:
                month       = datetime.datetime.strptime(self.account_period_id.date_start, '%Y-%m-%d').strftime('%m')
                year        = datetime.datetime.strptime(self.account_period_id.date_start, '%Y-%m-%d').strftime('%Y')
                last_day    = calendar.monthrange(int(year), int(month))[1]
                if self.payment_type=='payment1':
                    self.date_start  = time.strftime(str(year) + '-' + str(month) + '-' + '01')
                    self.date_end    = time.strftime(str(year) + '-' + str(month) + '-' + '15')
                elif self.payment_type=='payment2':
                    self.date_start  = time.strftime(str(year) + '-' + str(month) + '-' + '16')
                    self.date_end    = time.strftime(str(year) + '-' + str(month) + '-' + str(last_day))
                else:
                    self.date_start = self.account_period_id.date_start
                    self.date_end = self.account_period_id.date_stop

    @api.multi
    def unlink(self):
        for contractor in self:
            if contractor.state not in ['draft'] and self.doc_type_id.approval == True:
                raise UserError(_('Status dokumen Buku Kontraktor dengan nomor %s adalah %s.\n'
                                  'Buku Kontraktor hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') %
                                  (contractor.name, contractor.state.title()))
            if contractor.invoice_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Vendor Bill'))
            if contractor.move_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Journal Entry.\n Silahkan di Cancel terlebih dahulu'))
        contractor = super(lhm_contractor, self).unlink()
        return contractor

    @api.multi
    def button_confirm(self):
        move = self._account_move_entry()
        self.state = 'confirmed'

    @api.multi
    def button_draft(self):
        for contractor in self:
            if contractor.invoice_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Vendor Bill'))
            if contractor.move_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Journal Entry.\n Silahkan di Cancel terlebih dahulu'))
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        for contractor in self:
            if contractor.invoice_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Vendor Bill'))
            if contractor.move_id:
                contractor.move_id.unlink()
        self.state = 'cancel'

    @api.model
    def create(self, values):
        supplier_id     = self.env['lhm.utility'].search([('id', '=', values.get('supplier_id'))])
        period_id       = self.env['account.period'].search([('id', '=', values.get('account_period_id'))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (supplier_id.code or "") + "/" + year + "-" + month
        else:
            values['name']  = (supplier_id.code or "") + "/"
        return super(lhm_contractor, self).create(values)

    @api.multi
    def _account_move_entry(self):
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        grouped_lines = {}
        for buku_kontraktor in self:
            acc_dest = buku_kontraktor.supplier_id.account_payable_contractor_id
            if not acc_dest:
                raise ValidationError(_('Akun Perantara Hutang pada Kontraktor Belum diisi.\n'
                    'Silahkan isi akun tersebut terlebih dahulu'))
            journal_id = self.env['account.journal'].search([('type','=','general'),('code','like','MISC%')], limit=1)
            if not journal_id:
                raise ValidationError(_('General Jurnal belum didefinisikan.\n'
                    'Silahkan membuat General Jurnal terlebih dahulu'))
            total_lines = 0.0
            for line in buku_kontraktor.line_ids:
                key = (line.location_type_id, line.location_id, line.activity_id)
                if key not in grouped_lines.keys():
                    acc_src = line.activity_id.account_id
                    if not acc_src:
                        raise ValidationError(_('Aktivitas yg digunakan tidak memiliki Account Allocation.\n'
                            'Gunakan Aktivitas lain atau Lengkapi Allocation pada Aktifitas %s %s') % \
                            (line.activity_id.code,line.activity_id.name))
                    grouped_lines.update({key: {
                        'location_type': line.location_type_id,
                        'location': line.location_id,
                        'activity': line.activity_id,
                        'account_id': acc_src.id,
                        'journal_id': journal_id.id,
                        'partner_id': buku_kontraktor.supplier_id.id,
                        'date': buku_kontraktor.date_end,
                        'amount': 0.0,
                        'operating_unit_id': buku_kontraktor.operating_unit_id and buku_kontraktor.operating_unit_id.id or False,
                        }})
                grouped_lines[key]['amount'] += line.total
                total_lines += line.total
            for line in buku_kontraktor.line_vehicle_ids:
                key = (line.location_type_id, line.location_id, line.activity_id)
                if key not in grouped_lines.keys():
                    acc_src = line.activity_id.account_id
                    if not acc_src:
                        raise ValidationError(_('Aktivitas yg digunakan tidak memiliki Account Allocation.\n'
                            'Gunakan Aktivitas lain atau Lengkapi Allocation pada Aktifitas %s %s') % \
                            (line.activity_id.code,line.activity_id.name))
                    grouped_lines.update({key: {
                        'location_type': line.location_type_id,
                        'location': line.location_id,
                        'activity': line.activity_id,
                        'account_id': acc_src.id,
                        'journal_id': journal_id.id,
                        'partner_id': buku_kontraktor.supplier_id.id,
                        'date': buku_kontraktor.date_end,
                        'amount': 0.0,
                        'operating_unit_id': buku_kontraktor.operating_unit_id and buku_kontraktor.operating_unit_id.id or False,
                        }})
                grouped_lines[key]['amount'] += line.total
                total_lines += line.total
            move_lines = []
            for line in grouped_lines.values():
                move_lines.append((0,0, self._prepare_move_line_entry(line)))
            # counterpart entry for all activity
            move_lines.append((0, 0, self._prepare_move_line_entry({
                    'account_id': acc_dest.id,
                    'journal_id': journal_id.id,
                    'partner_id': buku_kontraktor.supplier_id.id,
                    'date': buku_kontraktor.date_end,
                    'amount': -1*total_lines,
                    'operating_unit_id': buku_kontraktor.operating_unit_id and buku_kontraktor.operating_unit_id.id or False,
                    })))
            move = AccountMove.create({
                'journal_id': journal_id.id,
                'date': buku_kontraktor.date_end,
                # 'period_id': buku_kontraktor.account_period_id.id,
                'line_ids': move_lines,
                'operating_unit_id': buku_kontraktor.operating_unit_id and buku_kontraktor.operating_unit_id.id or False,
                'ref': buku_kontraktor.name
                })
            move.post()
            buku_kontraktor.write({'move_id': move.id})

    def _prepare_move_line_entry(self, line):
        # convert amount
        amount = line.get('amount', 0.0)
        return {
            'name': line.get('activity', False) and line['activity'].name or '/',
            'plantation_location_type_id': line.get('location_type', False) and line['location_type'].id or False,
            'plantation_location_id': line.get('location', False) and line['location'].id or False,
            'plantation_activity_id': line.get('activity', False) and line['activity'].id or False,
            'account_id': line.get('account_id', False) and line['account_id'] or False,
            'journal_id': line.get('journal_id', False) and line['journal_id'] or False,
            'date': line.get('date', False) and line['date'] or False,
            'debit': amount>0 and amount or 0.0,
            'credit': amount<0 and -1*amount or 0.0,
            'amount_currency': 0.0,
            'operating_unit_id': line.get('operating_unit_id', False) and line['operating_unit_id'] or False,
            'currency_id': False,
        }

    @api.multi
    def write(self, values):
        supplier_id     = self.env['lhm.utility'].search([('id', '=', values.get('supplier_id', self.supplier_id.id))])
        period_id       = self.env['account.period'].search([('id', '=', values.get('account_period_id', self.account_period_id.id))])
        if period_id:
            month           = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%m')
            year            = datetime.datetime.strptime(period_id.date_start, '%Y-%m-%d').strftime('%Y')
            values['name']  = (supplier_id.code or "") + "/" + year + "-" + month
        return super(lhm_contractor, self).write(values)

    @api.multi
    def get_material(self):
        move_obj            = self.env['stock.move']
        material_line_obj   = self.env['lhm.contractor.material.line']
        for contractor in self:
            # UPDATE line yg sudah terlanjur terbuat
            line_to_update = []
            line_to_delete = []
            for mat_line in sorted(contractor.material_line_ids, key=lambda x:x.date):
                if mat_line.realization>0.0 and mat_line.residual_qty>0.0:
                    line_to_update.append(mat_line)
                elif mat_line.realization>0.0 and mat_line.residual_qty==0.0:
                    line_to_delete.append(mat_line)
            for line in contractor.material_line_ids.filtered(lambda x: x.realization==0.0):
                if line.move_id.id in [x.move_id.id for x in line_to_update]:
                    line.write({
                            'stock_qty' : line.move_id.plantation_material_allocation,
                        })
            for line in contractor.material_line_ids.filtered(lambda x: x.realization==0.0):
                if line.move_id.id in [x.move_id.id for x in line_to_delete]:
                    line.unlink()
            # Tambah SKB baru
            for line in sorted(contractor.line_ids.filtered(lambda x: x.location_id \
                        and x.location_id.type_id.skb_declare), key=lambda x:x.date):
                domain = [
                        ('date', '<=', str(line.date) + ' 23:59:59'), 
                        ('skb', '=', True), ('state', '=', 'done'), 
                        ('plantation_location_id', '=', line.location_id.id), 
                        ('plantation_activity_id', '=', line.activity_id.id), 
                        ('origin_returned_move_id', '=', False),
                        ('pending_material_allocation', '>', 0.0),
                        ]
                current_material = material_line_obj.search([('line_id','=',line.id)])
                if current_material:
                    current_move = current_material.mapped('move_id')
                    domain.append(('id','not in',current_move.ids))
                pending_moves = move_obj.search(domain)
                for skb in pending_moves:
                    values_skb  = {
                        'name'              : skb.picking_id.bpb_number or '',
                        'date'              : line.date,
                        'product_id'        : skb.product_id.id,
                        'location_id'       : skb.plantation_location_id.id,
                        'activity_id'       : skb.plantation_activity_id.id,
                        'real_stock_qty'    : skb.product_uom_qty,
                        'stock_qty'         : skb.plantation_material_allocation,
                        'product_uom_id'    : skb.product_uom.id,
                        'move_id'           : skb.id,
                        'picking_id'        : skb.picking_id and skb.picking_id.id or False,
                        'contractor_id'     : contractor.id,
                        'line_id'           : line.id,
                    }
                    material_line_obj.create(values_skb)

class lhm_contractor_material_line(models.Model):
    _name           = 'lhm.contractor.material.line'
    _description    = 'LHM Contractor Material Line'

    name            = fields.Char("BPB", readonly=True)
    date            = fields.Date("Tanggal", )
    product_id      = fields.Many2one("product.product", string="Product", ondelete="restrict")
    activity_id     = fields.Many2one("lhm.activity", string="Aktivitas", ondelete="restrict")
    activity_name   = fields.Char(related="activity_id.name", string="Name", ondelete="restrict")
    location_id     = fields.Many2one("lhm.location", string="Lokasi", ondelete="restrict")
    real_stock_qty  = fields.Float('SKB Qty', digits=dp.get_precision('Product Unit of Measure'),)
    product_uom_id  = fields.Many2one("product.uom", string="UoM", ondelete="restrict")
    stock_qty       = fields.Float('Declared', digits=dp.get_precision('Product Unit of Measure'),)
    realization     = fields.Float('Qty Realisasi', digits=dp.get_precision('Product Unit of Measure'),)
    residual_qty    = fields.Float(compute='_get_residual', string='Residual', digits=dp.get_precision('Product Unit of Measure'),)
    move_id         = fields.Many2one("stock.move", string="Stock Move", ondelete="restrict")
    picking_id      = fields.Many2one("stock.picking", string="Stock Picking", ondelete="restrict")
    line_id         = fields.Many2one("lhm.contractor.line", string="Progress", ondelete="restrict")
    contractor_id   = fields.Many2one("lhm.contractor", "LHM Contractor", ondelete="cascade")

    @api.depends('realization')
    def _get_residual(self):
        for line in self:
            residual = line.real_stock_qty - line.stock_qty - line.realization
            # if residual < 0:
            #     line.residual_qty = residual
            #     raise UserError(_('Realisasi Salah.\n'
            #                     'Realisasi tidak dapat melebihi Jumlah yg di SKB'))
            # else:
            line.residual_qty = residual

class lhm_contractor_line(models.Model):
    _name           = 'lhm.contractor.line'
    _description    = 'LHM Contractor Line'

    @api.multi
    @api.depends("location_type_id","location_id")
    def _get_doc_activity_ids(self):
        for object in self:
            activity_list = []
            if object.contractor_id._context.get('default_type',object.contractor_id.type) == 'vendor':
                doc_id  = self.env['res.doc.type'].search([('code', '=', 'bkt')])[-1]
            else:
                doc_id  = self.env['res.doc.type'].search([('code', '=', 'bkta')])[-1]
            level_1     = self.env['lhm.activity'].search([('level', '=', 1)])[-1]
            avail_act   = self.env['lhm.activity'].search([('type_id', '=', object.location_type_id.id)])
            if doc_id:
                for act in avail_act:
                    if doc_id.id in act.doc_ids.ids:
                        activity_list.append(act.id)
            if level_1:
                activity_list.append(level_1.id)
            if (object.location_type_id and object.location_type_id.project) and object.location_id:
                project_ids = self.env['lhm.project'].search([('location_id', '=', object.location_id.id)])
                project_act = []
                avail = []
                if level_1:
                    avail.append(level_1.id)
                for project in project_ids:
                    project_act += [x.activity_id.id for x in project.line_ids]
                if project_act != []:
                    for act_project in project_act:
                        if act_project in activity_list:
                            avail.append(act_project)
                if avail != []:
                    object.doc_activity_ids = [(6, 0, avail)]
            else:
                object.doc_activity_ids = [(6, 0, activity_list)]

    name                = fields.Char(related='activity_id.name', readonly=True)
    date                = fields.Date("Tanggal", )
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    no_line             = fields.Boolean(string="Mandatory", related="location_type_id.no_line")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    doc_activity_ids    = fields.Many2many('lhm.activity', store=True, compute=_get_doc_activity_ids)
    nilai               = fields.Float('Hasil 1')
    uom_id              = fields.Many2one(comodel_name="product.uom", string="Satuan 1", ondelete="restrict")
    nilai2              = fields.Float('Hasil 2')
    uom2_id             = fields.Many2one(comodel_name="product.uom", string="Satuan 2", ondelete="restrict")
    unit_price          = fields.Float('Tarif Satuan')
    total               = fields.Float('Nilai', compute='_compute_harga_satuan', store=True, readonly=True)
    type                = fields.Selection([('vehicle','Alat'),('vendor','Vendor')], string='Type', related="contractor_id.type", readonly=True)
    supplier_id         = fields.Many2one(comodel_name="res.partner", related="contractor_id.supplier_id", readonly=True)
    contractor_vehicle  = fields.Boolean(string="Vehicle", related="contractor_id.contractor_vehicle", readonly=True)
    contractor_id       = fields.Many2one(comodel_name="lhm.contractor", string="Contractor", ondelete="cascade")
    tidak_ditagihkan    = fields.Boolean(string="Tidak Ditagihkan")

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            self.uom_id     = self.activity_id.uom_id and self.activity_id.uom_id.id or False
            self.uom2_id    = self.activity_id.uom2_id and self.activity_id.uom2_id.id or False

    @api.onchange('location_type_id')
    def _onchange_location_type_id(self):
        if self.location_type_id:
            self.location_id = False
            self.activity_id = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.activity_id = False

    @api.depends('unit_price', 'nilai')
    def _compute_harga_satuan(self):
        for harga in self:
            if harga.nilai and harga.unit_price:
                harga.total = harga.unit_price * harga.nilai

    @api.multi
    @api.constrains('date', 'location_id', 'activity_id')
    def _check_date_unique(self):
        for rec in self:
            rec._check_date_line()

    def _check_date_line(self):
        if not (self.date >= self.contractor_id.date_start and self.date <= self.contractor_id.date_end):
            raise UserError(_('Tanggal %s pada Buku Kontraktor tidak dalam Periode Pembayaran \n'
                              '%s - %s.\n'
                              'Ubah tanggal atau hapus baris di Daftar Buku Kontraktor') % (
                            self.date, self.contractor_id.date_start, self.contractor_id.date_end))
        domain          = []
        total_domain    = 0
        if self.date:
            domain.append(('date', '=', self.date))
            total_domain +=1
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
            total_domain += 1
        if self.activity_id:
            domain.append(('activity_id', '=', self.activity_id.id))
            total_domain += 1
        if self.type:
            domain.append(('type', '=', self.type))
            total_domain += 1
        if self.supplier_id:
            domain.append(('supplier_id', '=', self.supplier_id.id))
            total_domain += 1
        if self.unit_price:
            domain.append(('unit_price', '=', self.unit_price))
            total_domain += 1
        if total_domain == 6 and self.search_count(domain) > 1:
            raise UserError(_('Terjadi Duplikasi Data!!!!.\n'
                              'Tanggal          : %s.\n'
                              'Kode Lokasi      : %s.\n'
                              'Kode Aktivitas   : %s.\n'
                              'Ganti salah satu detail atau hapus baris yang sama') % (self.date, self.location_id.code, self.activity_id.code))
        return True

class lhm_contractor_vehicle_line(models.Model):
    _inherit        = 'lhm.contractor.line'
    _name           = 'lhm.contractor.vehicle.line'
    _description    = 'LHM Contractor Vehicle Line'

    @api.multi
    @api.depends("start_value", "end_value")
    def _compute_difference(self):
        for diff in self:
            diff.difference_value = diff.end_value - diff.start_value

    @api.multi
    @api.depends("activity_id")
    def _get_charge_activity_ids(self):
        for line in self:
            if line.activity_id and line.activity_id.charge_ids:
                line.filter_charge_ids = [(6, 0, [x.id for x in line.activity_id.charge_ids])]
            else:
                line.filter_charge_ids = []


    start_value         = fields.Float("km/hm Berangkat")
    end_value           = fields.Float("km/hm Kembali")
    difference_value    = fields.Float("km/hm Terpakai", compute="_compute_difference", store=True)
    vehicle_id          = fields.Many2one(comodel_name="lhm.utility", string="Alat", ondelete="restrict")
    charge_value        = fields.Float("Vol. Muatan")
    distance_value      = fields.Float("Jarak")
    filter_charge_ids   = fields.Many2many('lhm.charge.type', store=True, compute=_get_charge_activity_ids)
    charge_id           = fields.Many2one(comodel_name="lhm.charge.type", string="Muatan", ondelete="restrict")
    uom_charge_id       = fields.Many2one(comodel_name="product.uom", string="Satuan Muatan", ondelete="restrict")
    contractor_id       = fields.Many2one(comodel_name="lhm.contractor", string="Contractor", ondelete="cascade")

    @api.onchange('vehicle_id', 'date')
    def _onchange_vehicle_id(self):
        lhm_contractor_obj = self.env['lhm.contractor']
        context = self._context
        if self.vehicle_id and self.date:
            date = self.date and self.date or self.contractor_id.date_start
            if context.get('line_vehicle_ids'):
                line_dict = lhm_contractor_obj.resolve_2many_commands('line_vehicle_ids', context.get('line_vehicle_ids'))
                last_end_value = 0.0
                for x in line_dict:
                    if x['vehicle_id'] == self.vehicle_id.id and x['date'] <= date and x['end_value'] > last_end_value:
                        last_end_value = max([x['end_value'] for x in line_dict])
                self.start_value = last_end_value
            else:
                other_id    = self.search([('vehicle_id','=',self.vehicle_id.id),('date','<=',date),], order="date desc", limit=1)
                if other_id:
                    self.start_value = other_id.end_value


    @api.depends('unit_price', 'nilai', 'difference_value')
    def _compute_harga_satuan(self):
        for harga in self:
            if harga.nilai:
                harga.total = harga.unit_price * harga.nilai
            if harga.contractor_id and harga.difference_value and harga.unit_price:
                if harga.contractor_id.total_type == 'used' and harga.difference_value:
                    harga.total = harga.unit_price * harga.difference_value
                else:
                    harga.total = harga.unit_price * harga.nilai

    def _check_date_line(self):
        if not (self.date >= self.contractor_id.date_start and self.date <= self.contractor_id.date_end):
            raise UserError(_('Tanggal %s pada Buku Kontraktor tidak dalam Periode Pembayaran \n'
                              '%s - %s.\n'
                              'Ubah tanggal atau hapus baris di Daftar Buku Kontraktor') % (
                            self.date, self.contractor_id.date_start, self.contractor_id.date_end))
        domain          = []
        total_domain    = 0
        if self.date:
            domain.append(('date', '=', self.date))
            total_domain +=1
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
            total_domain += 1
        if self.activity_id:
            domain.append(('activity_id', '=', self.activity_id.id))
            total_domain += 1
        if self.type:
            domain.append(('type', '=', self.type))
            total_domain += 1
        if self.supplier_id:
            domain.append(('supplier_id', '=', self.supplier_id.id))
            total_domain += 1
        if self.vehicle_id:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
            total_domain += 1
        if self.unit_price:
            domain.append(('unit_price', '=', self.unit_price))
            total_domain += 1
        if total_domain == 7 and self.search_count(domain) > 1:
            raise UserError(_('Terjadi Duplikasi Data!!!!.\n'
                              'Tanggal          : %s.\n'
                              'Kode Lokasi      : %s.\n'
                              'Kode Aktivitas   : %s.\n'
                              'Ganti salah satu detail atau hapus baris yang sama') % (self.date, self.location_id.code, self.activity_id.code))
        return True
########################################### End Of Transaction Buku Kontraktor ##############################################
############################################### Transaction Nota Angkut Buah ################################################
class lhm_nab(models.Model):
    _name           = 'lhm.nab'
    _description    = 'Nota Angkut Buah'

    @api.one
    @api.depends('timbang_ksg_kbn', 'timbang_isi_kbn', 'timbang_isi_pks', 'timbang_ksg_pks', 'grading')
    def _compute_timbang(self):
        self.timbang_tara_kbn = self.timbang_isi_kbn - self.timbang_ksg_kbn
        self.timbang_tara_pks = self.timbang_isi_pks - self.timbang_ksg_pks
        self.netto = self.timbang_isi_pks - self.timbang_ksg_pks - self.grading

    @api.one
    @api.depends('line_ids')
    def _compute_janjang(self):
        if self.line_ids:
            total_janjang = 0
            for line_nab in self.line_ids:
                total_janjang = total_janjang + line_nab.qty_nab
            self.janjang_jml = total_janjang

    @api.depends('date_nab', 'state')
    def _compute_account_period_id(self):
        for plantation_nab in self:
            if plantation_nab.date_nab:
                period_id = self.env['account.period'].search([('date_start', '<=', plantation_nab.date_nab), ('date_stop', '>=', plantation_nab.date_nab), ('special', '=', False)])
                if period_id:
                    plantation_nab.account_period_id = period_id

    name                = fields.Char('No. Register', required=False)
    date_nab            = fields.Date("Tanggal", readonly=True, states={'draft': [('readonly',False)]})
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", compute='_compute_account_period_id', store=True)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    no_nab              = fields.Char('No. NAB Manual', readonly=True, states={'draft': [('readonly',False)]})
    afdeling_id         = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict", readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})
    driver              = fields.Char('Nama Supir', readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})
    vehicle_id          = fields.Many2one(comodel_name="lhm.utility", string="Kendaraan", ondelete="restrict", domain="[('type','=', 'vh')]", readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})
    vehicle_subtitute_id= fields.Many2one("lhm.utility", "Kendaraan Pengganti", ondelete="restrict", domain="[('type','=', 'vh')]", readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})
    reg_number          = fields.Char('Nomor Polisi', readonly=True, related="vehicle_id.reg_number", store=True)
    reg_number_subtitue = fields.Char('Nomor Polisi', readonly=True, related="vehicle_subtitute_id.reg_number", store=True)
    ownership           = fields.Selection('Kepemilikan', readonly=True, related="vehicle_id.ownership", store=True)
    ownership_subtitute = fields.Selection('Kepemilikan', readonly=True, related="vehicle_subtitute_id.ownership", store=True)
    timbang_ksg_kbn     = fields.Float('Timbangan Kosong Kebun', readonly=True, states={'draft': [('readonly',False)]})
    timbang_isi_kbn     = fields.Float('Timbangan Isi Kebun', readonly=True, states={'draft': [('readonly',False)]})
    timbang_tara_kbn    = fields.Float('Timbangan Tara', compute='_compute_timbang', store=True)
    janjang_jml         = fields.Float('Jumlah Janjang', compute='_compute_janjang', store=True)
    pks_id              = fields.Many2one(comodel_name="res.partner", string="Nama PKS", ondelete="restrict", readonly=True, states={'draft': [('readonly',False)]})
    date_pks            = fields.Date("Tanggal PKS", readonly=True, states={'draft': [('readonly',False)]})
    timbang_isi_pks     = fields.Float('Timbangan Isi PKS', readonly=True, states={'draft': [('readonly',False)]})
    timbang_ksg_pks     = fields.Float('Timbangan Kosong PKS', readonly=True, states={'draft': [('readonly',False)]})
    timbang_tara_pks    = fields.Float('Timbangan Tara', compute='_compute_timbang', store=True)
    afkir               = fields.Float('Afkir', readonly=True, states={'draft': [('readonly',False)]})
    grading             = fields.Float('Grading', readonly=True, states={'draft': [('readonly',False)]})
    netto               = fields.Float('Netto', compute='_compute_timbang', store=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids            = fields.One2many(comodel_name='lhm.nab.line', inverse_name='lhm_nab_id', string="Detail Nota Angkut Buah", readonly=True, states={'draft': [('readonly',False)], 'revision': [('readonly',False)]})
    confirmed           = fields.Boolean('Confirmed')
    cancelled           = fields.Boolean('Cancelled')
    force_edit          = fields.Boolean('Revisi')
    state               = fields.Selection(compute='_get_state', store=True, selection=[
                                ('draft', 'New'), ('cancel', 'Cancelled'),
                                ('confirmed', 'Confirmed'), ('done', 'Done'), ('revision','Revisi')], string='Status',
                                copy=False, default='draft', index=True, readonly=True,
                                help="* New: Dokumen Baru.\n"
                                     "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                     "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                     "* Done: Dokumen Sudah Selesai Diproses. \n")
    invoice_id          = fields.Many2one('account.invoice', 'NAB Invoice')
    plasma_invoice_id   = fields.Many2one('account.invoice', 'NAB Invoice Plasma')
    contractor_id       = fields.Many2one('res.partner', 'Kontraktor', readonly=True, states={'draft': [('readonly',False)], 'confirmed': [('readonly',False)], 'revision': [('readonly',False)]})
    lhm_contractor_id   = fields.Many2one('lhm.contractor', 'Contractor Book', readonly=True)

    _order = "date_nab desc"

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'vdata_panen_nab_naf')
        self._cr.execute("""
            CREATE VIEW vdata_panen_nab_naf AS (
              SELECT 'panen'::text AS grp,
                lrb.tgl_panen,
                lpb.afdeling_id,
                lpb.id AS block_id,
                lrb.tgl_panen AS tgl_trans,
                sum(lrb.value) AS jjg_qty
               FROM (lhm_restan_balance lrb
                 LEFT JOIN lhm_plant_block lpb ON ((lpb.id = lrb.block_id)))
              GROUP BY lrb.tgl_panen, lpb.afdeling_id, lpb.id
            UNION ALL
             SELECT 'panen'::text AS grp,
                ltpl.date AS tgl_panen,
                lpb.afdeling_id,
                lpb.id AS block_id,
                ltpl.date AS tgl_trans,
                sum(ltpl.nilai) AS jjg_qty
               FROM (((lhm_transaction lt
                 LEFT JOIN lhm_transaction_process_line ltpl ON ((lt.id = ltpl.lhm_id)))
                 LEFT JOIN lhm_activity la ON ((la.id = ltpl.activity_id)))
                 LEFT JOIN lhm_plant_block lpb ON ((lpb.location_id = ltpl.location_id)))
              WHERE ((la.is_panen IS TRUE) AND ((lt.state)::text = ANY (ARRAY[('done'::character varying)::text, ('close'::character varying)::text])))
              GROUP BY ltpl.date, lpb.afdeling_id, lpb.id
            UNION ALL
             SELECT 'nab'::text AS grp,
                lnl.tgl_panen,
                lpb.afdeling_id,
                lnl.block_id,
                ln.date_pks AS tgl_trans,
                (- sum(lnl.qty_nab)) AS jjg_qty
               FROM ((lhm_nab ln
                 LEFT JOIN lhm_nab_line lnl ON ((lnl.lhm_nab_id = ln.id)))
                 LEFT JOIN lhm_plant_block lpb ON ((lpb.id = lnl.block_id)))
              WHERE (((ln.state)::text = ANY (ARRAY[('confirmed'::character varying)::text, ('done'::character varying)::text])) AND (lnl.block_id IS NOT NULL))
              GROUP BY lnl.tgl_panen, lpb.afdeling_id, lnl.block_id, ln.date_pks
            UNION ALL
             SELECT 'naf'::text AS grp,
                lnal.tgl_panen,
                lpb.afdeling_id,
                lnal.block_id,
                lna.date_naf AS tgl_trans,
                (- sum(lnal.qty)) AS jjg_qty
               FROM ((lhm_nab_afkir lna
                 LEFT JOIN lhm_nab_afkir_line lnal ON ((lnal.lhm_nab_afkir_id = lna.id)))
                 LEFT JOIN lhm_plant_block lpb ON ((lpb.id = lnal.block_id)))
              WHERE (((lna.state)::text = ANY (ARRAY[('confirmed'::character varying)::text, ('done'::character varying)::text])) AND (lnal.block_id IS NOT NULL))
              GROUP BY lnal.tgl_panen, lpb.afdeling_id, lnal.block_id, lna.date_naf
            )""")

    @api.onchange('vehicle_id' ,'vehicle_subtitute_id')
    def onchange_vehicle(self):
        if self.vehicle_id:
            self.contractor_id = self.vehicle_id and self.vehicle_id.partner_id and self.vehicle_id.partner_id.id or False
        elif self.vehicle_subtitute_id:
            self.contractor_id = self.vehicle_subtitute_id and self.vehicle_subtitute_id.partner_id and self.vehicle_subtitute_id.partner_id.id or False

    @api.one
    @api.depends('confirmed', 'invoice_id', 'invoice_id.state', 'cancelled', 'force_edit')
    def _get_state(self):
        if self.confirmed:
            if self.sudo().invoice_id and self.sudo().invoice_id.state not in ('draft', 'cancel'):
                self.state = 'done'
            else:
                self.state = 'confirmed'
        elif self.cancelled:
            self.state = 'cancel'
        elif self.force_edit:
            self.state = 'revision'
        else:
            self.state = 'draft'

    @api.multi
    def unlink(self):
        for nab in self:
            if nab.state not in ['draft']:
                raise UserError(_('Status Nota Angkut Buah dengan nomor %s adalah %s.\n'
                                  'Nota Angkut Buah hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (nab.name, nab.state.title()))
        nab = super(lhm_nab, self).unlink()
        return nab

    @api.multi
    def button_confirm(self):
        if not self.pks_id:
            raise UserError(_('Nama PKS masih Kosong.\n'
                                'Silahkan isi Nama PKS tersebut terlebih dahulu'))
        if self.line_ids:
            for line in self.line_ids:
                if line.qty_nab <= 0 :
                    raise UserError(_('Total NAB harus lebih dari 0.\n'
                                'Perbaiki data pada lokasi %s sebelum diconfirm!!')%(line.block_id.code or '-'))
        else:
            raise UserError(_('Detail Nota Angkut Buah Kosong.\n'
                                'Silahkan isi Detail Nota Angkut Buah terlebih dahulu'))
        self.state = 'confirmed'
        self.confirmed = True
        self.line_ids.link_to_lhm_progress()
        self.line_ids.allocate_nab_line_to_lhm_line()

    @api.multi
    def button_draft(self):
        for nab in self:
            if nab.sudo().invoice_id and nab.sudo().invoice_id.state not in ('draft','cancel'):
                raise UserError(_('Anda tidak dapat meng-Cancel Nota Angkut Buah \n'
                                  'yang telah memiliki Invoice.\n'
                                  'Silahkan Cancel Invoice tersebut terlebih dahulu. Invoice : %s')%nab.invoice_id.internal_number)
            for link_lhm in nab.line_ids.mapped('lhm_line_ids'):
                link_lhm.unlink()
        self.state = 'draft'
        self.confirmed = False
        self.cancelled = False
        self.line_ids.write({'lhm_progress_ids': [(5,False,False)]})

    @api.multi
    def button_cancel(self):
        self.state = 'cancel'
        self.confirmed = False
        self.cancelled = True

    @api.multi
    def button_revise(self):
        for nab in self:
            for link_lhm in nab.line_ids.mapped('lhm_line_ids'):
                link_lhm.unlink()
        self.confirmed = False
        self.force_edit = True
        self.line_ids.write({'lhm_progress_ids': [(5,False,False)]})

    @api.multi
    def button_approve_revision(self):
        self.confirmed = True
        self.force_edit = False
        self.line_ids.link_to_lhm_progress()
        self.line_ids.allocate_nab_line_to_lhm_line()

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('lhm.nab') or _('New')
        return super(lhm_nab, self).create(values)

class lhm_nab_line(models.Model):
    _name               = 'lhm.nab.line'
    _description        = 'LHM Nota Angkut Buah Line'

    @api.one
    @api.depends('block_id', 'tgl_panen')
    def _compute_panen(self):
        if self.block_id and self.tgl_panen:
            total_lhm       = 0
            total_nab       = 0
            if isinstance(self.id, int):
                domain = [
                    ('block_id', '=', self.block_id.id),
                    ('tgl_panen', '=', self.tgl_panen),
                    ('id', '!=', self.id)]
            else:
                domain = [
                    ('block_id', '=', self.block_id.id),
                    ('tgl_panen', '=', self.tgl_panen)]
            other_nab       = self.env['lhm.nab.line'].search(domain)
            progress_ids    = self.env['lhm.transaction.process.line'].search([('date', '=', self.tgl_panen), ('location_id', '=', self.block_id.location_id.id)])
            balance_ids     = self.env['lhm.restan.balance'].search([('tgl_panen', '=', self.tgl_panen), ('block_id', '=', self.block_id.id)])
            if balance_ids:
                for balance in balance_ids:
                    total_lhm += balance.value
            if progress_ids:
                for progress in progress_ids:
                    if progress.activity_id.is_panen:
                        total_lhm += progress.nilai
            if other_nab:
                for nab in other_nab:
                    total_nab += nab.qty_nab
            self.qty_panen_lhm  = total_lhm
            self.qty_akum_nab   = total_nab
            self.qty_sisa_panen = total_lhm - total_nab

    @api.multi
    @api.depends('lhm_nab_id.state','lhm_line_ids','lhm_line_ids.lhm_id.state',
        'lhm_line_ids.lhm_line_id.location_id','lhm_line_ids.lhm_line_id.activity_id',
        'lhm_line_ids.lhm_line_id.work_result')
    def _check_allocation_state(self):
        for line in self:
            # total_allocation = sum(line.lhm_line_ids.mapped('nilai'))
            total_panen = sum(line.mapped('lhm_progress_ids').mapped('nilai'))
            total_allocation = 0.0
            for xline in line.lhm_line_ids:
                if xline.lhm_line_id and xline.lhm_line_id.activity_id.is_panen \
                        and xline.lhm_line_id.location_id.id==line.block_id.location_id.id:
                    total_allocation+=(xline.lhm_line_id.work_result/total_panen)*line.qty_nab
            if round(total_allocation,2) < line.qty_nab:
                line.pending_allocation = True
            else:
                line.pending_allocation = False

    name                = fields.Char('Name', related="lhm_nab_id.name", store=True)
    block_id            = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi", ondelete="restrict")
    tgl_panen           = fields.Date("Tgl. Panen")
    qty_panen_lhm       = fields.Float("Total Panen", compute="_compute_panen", store=True)
    qty_akum_nab        = fields.Float("Akumulasi NAB", compute="_compute_panen", store=True)
    qty_sisa_panen      = fields.Float("Sisa Panen", compute="_compute_panen", store=True)
    qty_nab             = fields.Float("Total NAB")
    lhm_nab_id          = fields.Many2one(comodel_name="lhm.nab", string="Nota Buah Angkut", ondelete="cascade")
    lhm_progress_ids    = fields.Many2many('lhm.transaction.process.line', 'lhm_process_nab_line_rel', 'nab_line_id', 'progress_id', 'LHM Progress Ref')
    lhm_line_ids        = fields.One2many('lhm.transaction.line.nab.line', 'nab_line_id', 'LHM Detail')
    pending_allocation  = fields.Boolean('Pending Allocaton', compute='_check_allocation_state', store=True)

    @api.multi
    def compute_weight(self):
        self.ensure_one()
        weight = 0.0
        weight = (self.qty_nab*self.block_id.with_context({'date': self.lhm_nab_id.date_pks})._get_rate_bjr()) * self.lhm_nab_id.netto \
            / sum([x.qty_nab*x.block_id.with_context({'date': self.lhm_nab_id.date_pks})._get_rate_bjr() for x in self.lhm_nab_id.line_ids])
        return weight

    @api.multi
    def link_to_lhm_progress(self):
        for line in self:
            lhm_lines = self.env['lhm.transaction.process.line'].search([ \
                ('location_id','=',line.block_id.location_id.id), 
                ('lhm_id.state','!=','draft'), 
                ('lhm_id.date','=',line.tgl_panen), 
                ('activity_id.is_panen','=',True)
                ])
            if not lhm_lines:
                continue
            else:
                line.write({'lhm_progress_ids': [(6,0,lhm_lines.ids)]})
                #Trigger Function
                lhm_lines.write({'nab_line_ids': []})

    @api.multi
    def allocate_nab_line_to_lhm_line(self):
        for nab_line in self.filtered(lambda x: x.pending_allocation):
            vals = []
            total_panen = sum(nab_line.mapped('lhm_progress_ids').mapped('nilai'))
            if not nab_line.mapped('lhm_progress_ids'):
                raise ValidationError(_("Tidak dapat menemukan LHM.\nSilahkan \
                        input LHM dan Progress LHMnya sebelum membuat NAB"))
            if total_panen < nab_line.qty_nab:
                raise ValidationError(_("Total Progress Panen dari LHM untuk Blok %s lebih \n \
                        sedikit dibandingkan dengan NAB yg dikeluarkan"))
                # continue
            for progress in nab_line.lhm_progress_ids:
                lhm_lines = progress.lhm_id.mapped('lhm_line_ids').filtered(lambda x: x.location_id==progress.location_id and x.activity_id==progress.activity_id and x.activity_id.is_panen)
                # total_panen = sum(lhm_lines.mapped('work_result'))
                for line in lhm_lines:
                    janjang = total_panen and (line.work_result/total_panen)*nab_line.qty_nab or 0.0
                    berat = total_panen and (line.work_result/total_panen)*nab_line.compute_weight() or 0.0
                    vals.append((0,0,{
                        'lhm_line_id': line.id,
                        'nab_line_id': nab_line.id,
                        'nilai': janjang,
                        'uom_id': line.satuan_id and line.satuan_id.id or False,
                        'nilai2': berat,
                    }))
                    # self.env['lhm.transaction.line.nab.line'].create(vals)
            if vals:
                nab_line.write({'lhm_line_ids': vals})

    @api.model
    def _cron_linked_to_nab(self):
        pending_line = self.search([('lhm_progress_ids','=',False), ('lhm_nab_id.state','not in',['draft','revision'])])
        pending_line.link_to_lhm_progress()
        pending_line = self.search([('pending_allocation','=',True), ('lhm_nab_id.state','not in',['draft','revision'])])
        pending_line.allocate_nab_line_to_lhm_line()
    # @api.multi
    # @api.constrains('tgl_panen', 'block_id', 'lhm_nab_id')
    # def _check_attendance_id(self):
    #     for record in self:
    #         record._check_parent_one()
	#
    # def _check_parent_one(self):
    #     if self.tgl_panen and self.block_id and self.lhm_nab_id:
    #         if isinstance(self.lhm_nab_id.id, int):
    #             domain = [
    #                 ('tgl_panen', '=', self.tgl_panen),
    #                 ('block_id', '=', self.block_id.id),
    #                 ('lhm_nab_id', '=', self.lhm_nab_id.id),
    #                 ('id','!=',self.id)]
    #             nab_line = self.search(domain)
    #             if nab_line:
    #                 raise UserError(_(
    #                     'Anda tidak dapat membuat nota angkut buah dengan nama blok %s dan tanggal %s karena terjadi duplikasi data!') % (
    #                                 self.block_id.name, self.tgl_panen))
    #     return True

    # @api.onchange('qty_sisa_panen', 'qty_nab')
    # def onchange_qty_nab(self):
    #     if self.qty_sisa_panen and self.qty_nab:
    #         if self.qty_sisa_panen < self.qty_nab:
    #             self.qty_nab = 0.00
    #             return {
    #                 'warning': {'title': _('Kesalahan Input Data'),
    #                             'message': _("Total Tidak boleh lebih besar daripada sisa")},
    #             }
########################################### End Of Transaction Nota Angkut Buah #############################################
################################################## Link NAB and LHM ####################################################
class lhm_transaction_line_nab_line(models.Model):
    _name = 'lhm.transaction.line.nab.line'

    lhm_line_id = fields.Many2one('lhm.transaction.line','LHM Line Ref', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='lhm_line_id.employee_id', string='Karyawan')
    lhm_id = fields.Many2one('lhm.transaction', related='lhm_line_id.lhm_id', string='LHM Ref', readonly=True)
    nab_line_id = fields.Many2one('lhm.nab.line','NAB Line Ref', ondelete='cascade')
    nab_id = fields.Many2one('lhm.nab', related='nab_line_id.lhm_nab_id', string='NAB Ref', readonly=True, store=True)
    nab_date = fields.Date(related='nab_id.date_nab', string='NAB Date', readonly=True, store=True)
    nab_date_pks = fields.Date(related='nab_id.date_pks', string='PKS Date', readonly=True, store=True)
    nilai = fields.Float('Nilai')
    uom_id = fields.Many2one('product.uom', 'Satuan 1')
    nilai2 = fields.Float('Berat')
    uom_id2 = fields.Many2one('product.uom', 'Satuan 2')

    @api.multi
    @api.constrains('lhm_line_id', 'nab_line_id')
    def _check_double_link(self):
        check = True
        for line in self:
            if line.lhm_line_id:
                other_line = self.search([('id','!=',line.id),('lhm_line_id','=',line.lhm_line_id.id),('nab_line_id','=',line.nab_line_id.id)])
                if other_line:
                    raise ValidationError(_('Alokasi antara Detail NAB dan Detail LHM hanya bisa 1 kali!'))
########################################### End Of Link NAB and LHM #############################################
################################################## Transaction Afkir NAB ####################################################
class lhm_nab_afkir(models.Model):
    _name = 'lhm.nab.afkir'
    _description = 'Nota Afkir Buah'
    
    @api.one
    @api.depends('line_ids')
    def _compute_janjang(self):
        if self.line_ids:
            total_janjang = 0
            for line_nab_afkir in self.line_ids:
                total_janjang = total_janjang + line_nab_afkir.qty
            self.janjang_jml = total_janjang

    @api.depends('date_naf', 'state')
    def _compute_account_period_id(self):
        for plantation_naf in self:
            if plantation_naf.date_naf:
                period_id = self.env['account.period'].search([('date_start', '<=', plantation_naf.date_naf), ('date_stop', '>=', plantation_naf.date_naf), ('special', '=', False)])
                if period_id:
                    plantation_naf.account_period_id = period_id

    name                = fields.Char('No. Register', required=False)
    date_naf            = fields.Date("Tanggal")
    account_period_id   = fields.Many2one(comodel_name="account.period", string="Accounting Periode", ondelete="restrict", compute='_compute_account_period_id', readonly=True, store=True)
    date_start          = fields.Date(related="account_period_id.date_start", string="Range Start Date", readonly=1)
    date_stop           = fields.Date(related="account_period_id.date_stop", string="Range End Date", readonly=1)
    no_naf              = fields.Char('BA Afkir')
    afdeling_id         = fields.Many2one(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    janjang_jml         = fields.Float('Jumlah Janjang', readonly=True, compute='_compute_janjang', store=True)
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids            = fields.One2many(comodel_name='lhm.nab.afkir.line', inverse_name='lhm_nab_afkir_id', string="Detail Nota Angkut Buah", )
    state               = fields.Selection([
                                ('draft', 'New'), ('cancel', 'Cancelled'),
                                ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status',
                                copy=False, default='draft', index=True, readonly=True,
                                help="* New: Dokumen Baru.\n"
                                     "* Cancelled: Dokumen Telah Dibatalkan.\n"
                                     "* Confirmed: Dokumen Sudah Diperiksa Pihak Terkait.\n"
                                     "* Done: Dokumen Sudah Selesai Diproses. \n")

    @api.multi
    def unlink(self):
        for nab in self:
            if nab.state not in ['draft']:
                raise UserError(_('Status Nota Angkut Buah dengan nomor %s adalah %s.\n'
                                  'Nota Angkut Buah hanya bisa dihapus pada status New.\n'
                                  'Hubungi Administrator untuk info lebih lanjut') % (nab.name, nab.state.title()))
        nab = super(lhm_nab_afkir, self).unlink()
        return nab
    
    @api.multi
    def button_confirm(self):
        self.state = 'confirmed'
        self.line_ids.link_to_lhm_progress()
    
    @api.multi
    def button_draft(self):
        self.state = 'draft'
    
    @api.multi
    def button_cancel(self):
        self.state = 'cancel'
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('lhm.nab.afkir') or _('New')
        return super(lhm_nab_afkir, self).create(values)

class lhm_nab_afkir_line(models.Model):
    _name = 'lhm.nab.afkir.line'
    _description = 'LHM Nota Angkut Buah Line'

    block_id = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi", ondelete="restrict")
    tgl_panen = fields.Date(" Tanggal Panen")
    qty = fields.Float('Jumlah Janjang')
    lhm_nab_afkir_id = fields.Many2one(comodel_name="lhm.nab.afkir", string="Afkir Nota Buah Angkut", ondelete="cascade")
    lhm_progress_ids    = fields.Many2many('lhm.transaction.process.line', 'lhm_process_nab_afkir_line_rel', 'nab_afkir_line_id', 'progress_id', 'LHM Progress Ref')

    @api.multi
    def link_to_lhm_progress(self):
        for line in self:
            lhm_lines = self.env['lhm.transaction.process.line'].search([
                ('location_id','=',line.block_id.location_id.id), 
                ('lhm_id.state','!=','draft'), 
                ('lhm_id.date','=',line.tgl_panen), 
                ('activity_id.is_panen','=',True)])
            if not lhm_lines:
                continue
            else:
                line.write({'lhm_progress_ids': [(6,0,lhm_lines.ids)]})
                #Trigger Function
                lhm_lines.write({'nab_afkir_line_ids': []})

    @api.model
    def _cron_linked_to_nab(self):
        pending_line = self.search([('lhm_progress_ids','=',False), ('lhm_nab_afkir_id.state','!=','draft')])
        pending_line.link_to_lhm_progress()
############################################## End Of Transaction Afkir NAB #################################################

############################################## Config Nomor Awal Rotasi Panen##############################################
class lhm_rotasi_panen_balace(models.Model):
    _name = 'lhm.rotasi.panen.balance'
    _description = 'LHM Nomor Akhir Rotasi Panen'

    period_id       = fields.Many2one(comodel_name="account.period", string="Periode Rotasi Panen", ondelete="restrict")
    is_manual       = fields.Boolean("Manual", default=False)
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    image           = fields.Binary(string='File Excel')
    image_filename  = fields.Char(string='File Name')
    rotasi_ids      = fields.One2many(comodel_name='lhm.rotasi.panen.balance.nomor', inverse_name='nomor_id', string="Nomor Awal Rotasi", )

    @api.multi
    def import_excel(self):
        if self.rotasi_ids:
            for lines in self.rotasi_ids:
                lines.unlink()
    
        data = base64.decodestring(self.image)
        wb = xlrd.open_workbook(file_contents=data)
    
        rotasi_obj = self.env['lhm.rotasi.panen.balance.nomor']
        sh = wb.sheet_by_index(0)
        for rx in range(sh.nrows):
            if rx > 0:
                if sh.cell(rx, 0) is not None:
                    val = sh.cell(rx, 0).value
                
                    if isinstance(val, float):
                        code_new = str(int(val))
                    else:
                        code_new = val
                
                    wt = self.env['lhm.plant.block']
                    block_id = wt.search([('code', '=', code_new)]).id

                    rotasi_obj.create({
                        'block_code': code_new or False,
                        'block_id': block_id,
                        'value': sh.cell(rx, 2).value or False,
                        'nomor_id': self.id
                    })

class lhm_rotasi_panen_balace_nomor(models.Model):
    _name           = 'lhm.rotasi.panen.balance.nomor'
    _description    = 'LHM Nomor Akhir Rotasi Panen Detail'

    block_code  = fields.Char("Kode Blok")
    block_id    = fields.Many2one(comodel_name="lhm.plant.block", string="Nama Blok", ondelete="restrict")
    value       = fields.Integer('Nomor Akhir')
    nomor_id    = fields.Many2one(comodel_name="lhm.rotasi.panen.balance", string="No Akhir Rotasi Panen", ondelete="cascade")
########################################### End Of Config Nomor Awal Rotasi Panen  ##########################################



#---------------------------------------------------------------------------------------------------------------------------#