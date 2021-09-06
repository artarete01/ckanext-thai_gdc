from flask import Blueprint
import ckantoolkit as tk
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import g

import ckan.model as model
from ckanapi import LocalCKAN

import logging

from ckan.plugins.toolkit import (
        _, c, h, check_access, NotAuthorized, abort, render,
        redirect_to, request,
        )

# from ckanext.thai_gdc.controllers import dataset, banner, user
# from ckanext.thai_gdc.controllers.banner import BannerEditController
from ckanext.thai_gdc.controllers.dataset import (
    DatasetImportController, 
    DatasetManageController)

# from ckan.views.user import EditView as userEditView
from ckanext.thai_gdc.controllers.user import UserManageController
from ckan.views.home import CACHE_PARAMETERS
log = logging.getLogger(__name__)

thai_gdc = Blueprint('thai_gdc', __name__)


def user_active(id=None):
    '''
    thai gdc sysadmin active user under deleted
    '''
    if id: # user id
        try:
            
            context = {
                u'model': model,
                u'session': model.Session,
                u'user': g.user,
                u'auth_user_obj': g.userobj,
                u'for_view': True
            }
            check_access('user_update', context, {})
            user_dict = tk.get_action('user_show')(None, {'id':id})
            if user_dict and user_dict['state'] == 'deleted':
                user = model.User.get(user_dict['name'])
                user.state = model.State.ACTIVE
                user.save()
            return h.redirect_to(controller='user', action='read', id=id)
        except logic.ValidationError as e:
            return e


# thai_gdc.add_url_rule('/ckan-admin/banner-edit', view_func=edit_banner)
thai_gdc.add_url_rule('/ckan-admin/dataset-import', view_func=DatasetImportController._import_dataset)
thai_gdc.add_url_rule('/ckan-admin/clear-import-log', view_func=DatasetImportController.clear_import_log)
thai_gdc.add_url_rule('/dataset/edit-datatype/<package_id>', view_func=DatasetManageController.datatype_patch, methods=[u'GET', u'POST'])
thai_gdc.add_url_rule('/user/edit/user_active', view_func=user_active, methods=[u'POST',])
thai_gdc.add_url_rule('/user/edit/user_active/<id>', view_func=user_active, methods=[u'POST',])


def get_blueprints():
    return [thai_gdc]