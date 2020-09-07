# -*- coding: utf-8 -*-

from odoo import models, fields, api

class res_partner(models.Model):
    _inherit = 'res.partner'

    
    
    npwp 				= fields.Char('NPWP')
    alamat_npwp 		= fields.Char('Alamat NPWP')



    #test#