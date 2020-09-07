# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import time
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class OrmProcedure(models.Model):
	_name = "orm.procedure"
	_description = "ORM Procedure"
	
	name = fields.Char('Procedure Name', size=128, required=True)
	exec_text = fields.Text('Procedure to Execute', required=True)
	result = fields.Text('Result')

	_order = "id desc"

	@api.multi
	def execute_procedure(self):
		for procedure in self:
			text_procedure=compile(procedure.exec_text,'<string>', 'exec')
			exec(text_procedure)
			procedure.write({"result":"%s\n%s"%(procedure.result,result)})
		return True