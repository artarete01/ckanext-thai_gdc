# -*- coding: utf-8 -*-
import ckan.plugins as p
import ckan.lib.helpers as helpers
from pylons import config
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import ckan.lib.uploader as uploader
import six
import time
import logging

from ckan.plugins.toolkit import (
    _, c, h, BaseController, check_access, NotAuthorized, abort, render,
    redirect_to, request,
    )

from ckan.controllers.home import CACHE_PARAMETERS
import ckan.logic.schema as schema_
import ckan.lib.app_globals as app_globals

_validate = dict_fns.validate
ValidationError = logic.ValidationError

log = logging.getLogger(__name__)

class BannerEditController(BaseController):
    
    def edit_banner(self):

        context = {'model': model,
                   'user': c.user, 'auth_user_obj': c.userobj}
        try:
            check_access('config_option_update', context, {})
        except logic.NotAuthorized:
            abort(403, _('Need to be system administrator to administer'))

        items = [
            {'name': 'ckan.promoted_banner', 'control': 'image_upload', 'label': _('Promoted banner'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
                'field_url': 'ckan.promoted_banner', 'field_upload': 'promoted_banner_upload', 'field_clear': 'clear_promoted_banner_upload'},
            {'name': 'ckan.search_background', 'control': 'image_upload', 'label': _('Search background'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
                'field_url': 'ckan.search_background', 'field_upload': 'search_background_upload', 'field_clear': 'clear_search_background_upload'},
            {'name': 'ckan.favicon', 'control': 'favicon_upload', 'label': _('Site favicon'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
                'field_url': 'ckan.favicon', 'field_upload': 'favicon_upload', 'field_clear': 'clear_favicon_upload'},
        ]
        data = request.POST
        if 'save' in data:
            try:
                # really?
                data_dict = logic.clean_dict(
                    dict_fns.unflatten(
                        logic.tuplize_dict(
                            logic.parse_params(
                                request.POST, ignore_keys=CACHE_PARAMETERS))))

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
                    globals_keys = app_globals.app_globals_from_config_details.keys()
                    if key in globals_keys:
                        app_globals.set_app_global(key, value)

                # Update the config update timestamp
                model.set_system_info('ckan.config_update', str(time.time()))

                log.info('Updated config options: {0}'.format(data))
            except logic.ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                vars = {'data': data, 'errors': errors,
                        'error_summary': error_summary, 'form_items': items}
                return render('admin/banner_form.html', extra_vars=vars)

            h.redirect_to(controller='ckanext.thai_gdc.controllers.banner:BannerEditController', action='edit_banner')

        schema = logic.schema.update_configuration_schema()
        data = {}
        for key in schema:
            data[key] = config.get(key)

        vars = {'data': data, 'errors': {}, 'form_items': items}
        return render('admin/banner_form.html', extra_vars=vars)
