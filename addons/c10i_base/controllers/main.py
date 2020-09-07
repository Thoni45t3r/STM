# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import ast
from odoo.addons.web.controllers.main import Home
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import pytz
import datetime
import logging

from odoo import http
from odoo.http import request
_logger = logging.getLogger(__name__)


def set_background():
    param_obj = request.env['ir.config_parameter'].sudo()
    request.params['disable_footer'] = ast.literal_eval(param_obj.get_param('login_form_disable_footer')) or False
    request.params['disable_database_manager'] = ast.literal_eval(
        param_obj.get_param('login_form_disable_database_manager')) or False
    #modified by deby
    request.params['background_src'] = param_obj.get_param('login_form_background_default') or ''
    ################################################################################################################################

    # change_background = ast.literal_eval(param_obj.get_param('login_form_change_background_by_hour')) or False
    # if change_background:
    #     config_login_timezone = param_obj.get_param('login_form_change_background_timezone')
    #     tz = config_login_timezone and pytz.timezone(config_login_timezone) or pytz.utc
    #     current_hour = datetime.datetime.now(tz=tz).hour or 10
    #
    #     if (current_hour >= 0 and current_hour < 3) or (current_hour >= 18 and current_hour < 24):  # Night
    #         request.params['background_src'] = param_obj.get_param('login_form_background_night') or ''
    #     elif current_hour >= 3 and current_hour < 7:  # Dawn
    #         request.params['background_src'] = param_obj.get_param('login_form_background_dawn') or ''
    #     elif current_hour >= 7 and current_hour < 16:  # Day
    #         request.params['background_src'] = param_obj.get_param('login_form_background_day') or ''
    #     else:  # Dusk
    #         request.params['background_src'] = param_obj.get_param('login_form_background_dusk') or ''
    # else:
    #     request.params['background_src'] = param_obj.get_param('login_form_background_default') or ''


#----------------------------------------------------------
# Odoo Web web Controllers
#----------------------------------------------------------
class LoginHome(Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        set_background()
        return super(LoginHome, self).web_login(redirect, **kw)


class AuthSignupHomeInherit(AuthSignupHome):

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        set_background()
        return super(AuthSignupHomeInherit, self).web_auth_reset_password(*args, **kw)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        set_background()
        return super(AuthSignupHomeInherit, self).web_auth_signup(*args, **kw)
