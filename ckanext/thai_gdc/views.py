import six
import time
from flask import Blueprint
from flask.views import MethodView
import ckantoolkit as tk
import ckan.logic as logic
import ckan.logic.schema as schema_
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import g
import ckan.lib.uploader as uploader
import ckan.lib.app_globals as app_globals
import ckan.model as model
from ckanapi import LocalCKAN

import logging

from ckan.plugins.toolkit import (
        _, c, h, check_access, NotAuthorized, abort, render,
        redirect_to, request, config
        )

# from ckanext.thai_gdc.controllers import dataset, banner, user
# from ckanext.thai_gdc.controllers.banner import BannerEditController
from ckanext.thai_gdc.controllers.dataset import (
    DatasetImportController, 
    DatasetManageController)

# from ckan.views.user import EditView as userEditView
from ckanext.thai_gdc.controllers.user import UserManageController
from ckan.views.home import CACHE_PARAMETERS

_validate = dict_fns.validate
ValidationError = logic.ValidationError

log = logging.getLogger(__name__)

thai_gdc = Blueprint('thai_gdc', __name__)

def _get_banner_update():
    items = [
        {'name': 'ckan.promoted_banner', 'label': _('Promoted banner'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.promoted_banner', 'field_upload': 'promoted_banner_upload', 'field_clear': 'clear_promoted_banner_upload'},
        {'name': 'ckan.search_background', 'label': _('Search background'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.search_background', 'field_upload': 'search_background_upload', 'field_clear': 'clear_search_background_upload'},
        {'name': 'ckan.favicon', 'control': 'favicon_upload', 'label': _('Site favicon'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.favicon', 'field_upload': 'favicon_upload', 'field_clear': 'clear_favicon_upload'},
    ]

    return items
def _check_sysadmin():
    context = {'model': model,
            'user': c.user, 'auth_user_obj': c.userobj}
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        abort(403, _('Need to be system administrator to administer'))
    
    return context

@thai_gdc.before_request
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

class BannerConfig(MethodView):
    def get(self):
        _check_sysadmin()
        data = {}
        schema = logic.schema.update_configuration_schema()
        for key in schema:
            data[key] = config.get(key)
        vars = {'data': data, 'errors': {}, 'form_items': {}}
        return render('admin/banner_form.html', extra_vars=vars)
    
    def post(self):
        context = _check_sysadmin()
        try:
            req = request.form.copy()
            req.update(request.files.to_dict())
            data_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(
                            req, ignore_keys=CACHE_PARAMETERS))))
            del data_dict['save']
            c.revision_change_state_allowed = True

            schema = schema_.update_configuration_schema()

            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.promoted_banner',
                                'promoted_banner_upload', 'clear_promoted_banner_upload')
            upload.upload(uploader.get_max_image_size())
        
            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.search_background',
                                'search_background_upload', 'clear_search_background_upload')
            upload.upload(uploader.get_max_image_size())

            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.favicon',
                                'favicon_upload', 'clear_favicon_upload')
            upload.upload(uploader.get_max_image_size())

            data, errors = _validate(data_dict, schema, context)
            if errors:
                model.Session.rollback()
                raise ValidationError(errors)

            for key, value in six.iteritems(data):
            
                if key == 'ckan.promoted_banner' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))
                
                if key == 'ckan.search_background' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))
                
                if key == 'ckan.favicon' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))

                # Save value in database
                model.set_system_info(key, value)

                # Update CKAN's `config` object
                config[key] = value

                # Only add it to the app_globals (`g`) object if explicitly defined
                # there
                globals_keys = list(app_globals.app_globals_from_config_details.keys())
                if key in globals_keys:
                    app_globals.set_app_global(key, value)

            # Update the config update timestamp
            model.set_system_info('ckan.config_update', str(time.time()))
        except logic.ValidationError as e:
            items = _get_banner_update()
            data = request.form
            errors = e.error_dict
            error_summary = e.error_summary
            vars = dict(
                data = data,
                errors = errors,
                error_summary = error_summary,
                form_items = items
            )
            return render(u'admin/banner_form.html', extra_vars=vars)
        return h.redirect_to(u'thai_gdc.edit_banner')

thai_gdc.add_url_rule('/ckan-admin/banner-edit', view_func=BannerConfig.as_view(str(u'edit_banner')))
# thai_gdc.add_url_rule('/ckan-admin/dataset-import', view_func=DatasetImportController._import_dataset)
# thai_gdc.add_url_rule('/ckan-admin/clear-import-log', view_func=DatasetImportController.clear_import_log)
# thai_gdc.add_url_rule('/dataset/edit-datatype/<package_id>', view_func=DatasetManageController.datatype_patch, methods=[u'GET', u'POST'])
thai_gdc.add_url_rule('/user/edit/user_active', view_func=user_active, methods=[u'POST',])
thai_gdc.add_url_rule('/user/edit/user_active/<id>', view_func=user_active, methods=[u'POST',])


def get_blueprints():
    return [thai_gdc]