# -*- coding: utf-8 -*-
import ckan.plugins as p
import ckan.lib.helpers as helpers
from pylons import config

_ = p.toolkit._


class OpendController(p.toolkit.BaseController):
    controller = 'ckanext.thai_gdc.controllers.opend:OpendController'

    def index(self):
        return 
