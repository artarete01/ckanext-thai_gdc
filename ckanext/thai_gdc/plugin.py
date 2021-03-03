#!/usr/bin/env python
# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import _, c

import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan.lib.plugins import DefaultTranslation
from ckan import logic
import re
from itertools import count
from six import string_types
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH)
from ckanext.thai_gdc import helpers as noh

import logging
import os

log = logging.getLogger(__name__)

class Thai_GDCPlugin(plugins.SingletonPlugin, DefaultTranslation, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        if toolkit.check_ckan_version(max_version='2.9'):
            toolkit.add_ckan_admin_tab(config_, 'banner_edit', 'Banner Editor')
            toolkit.add_ckan_admin_tab(config_, 'dataset_import', 'Dataset Importer')
        else:
            toolkit.add_ckan_admin_tab(config_, 'banner_edit', 'Banner Editor', icon='wrench')
            toolkit.add_ckan_admin_tab(config_, 'dataset_import', 'Dataset Importer', icon='cloud-upload')
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_public_directory(config_, 'fanstatic')
        toolkit.add_resource('fanstatic', 'thai_gdc')

        try:
            from ckan.lib.webassets_tools import add_public_path
        except ImportError:
            pass
        else:
            asset_path = os.path.join(
                os.path.dirname(__file__), 'fanstatic'
            )
            add_public_path(asset_path, '/')
        
        config_['ckan.tracking_enabled'] = 'true'
        config_['scheming.dataset_schemas'] = 'ckanext.thai_gdc:ckan_dataset.json'
        config_['ckan.activity_streams_enabled'] = 'true'
        config_['ckan.auth.user_delete_groups'] = 'false'
        config_['ckan.auth.user_delete_organizations'] = 'false'
        config_['ckan.auth.public_user_details'] = 'false'
        config_['ckan.datapusher.assume_task_stale_after'] = '60'
        config_['ckan.locale_default'] = 'th'
        config_['ckan.locale_order'] = 'en th pt_BR ja it cs_CZ ca es fr el sv sr sr@latin no sk fi ru de pl nl bg ko_KR hu sa sl lv'
        config_['ckan.datapusher.formats'] = 'csv xls xlsx tsv application/csv application/vnd.ms-excel application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        config_['ckan.group_and_organization_list_all_fields_max'] = '200'
        config_['ckan.group_and_organization_list_max'] = '200'
        config_['ckan.datasets_per_page'] = '200'
    
    def before_map(self, map):

        map.connect(
            'banner_edit',
            '/ckan-admin/banner-edit',
            action='edit_banner',
            ckan_icon='wrench',
            controller='ckanext.thai_gdc.controllers.banner:BannerEditController',
            )
        map.connect(
            'dataset_import',
            '/ckan-admin/dataset-import',
            action='import_dataset',
            ckan_icon='cloud-upload',
            controller='ckanext.thai_gdc.controllers.dataset:DatasetImportController',
            )
        map.connect(
            'clear_import_log',
            '/ckan-admin/clear-import-log',
            action='clear_import_log',
            controller='ckanext.thai_gdc.controllers.dataset:DatasetImportController',
            )

        return map

    def update_config_schema(self, schema):

        ignore_missing = toolkit.get_validator('ignore_missing')
        remove_whitespace = toolkit.get_validator('remove_whitespace')
        unicode_safe = toolkit.get_validator('unicode_safe')

        schema.update({
            'ckan.site_org_address': [ignore_missing, unicode],
            'ckan.site_org_contact': [ignore_missing, unicode],
            'ckan.site_org_email': [ignore_missing, unicode],
            'ckan.site_policy_link': [ignore_missing, unicode],
            'ckan.promoted_banner': [ignore_missing, unicode_safe],
            'promoted_banner_upload': [ignore_missing, unicode_safe],
            'clear_promoted_banner_upload': [ignore_missing, unicode_safe],
            'ckan.search_background': [ignore_missing, unicode_safe],
            'search_background_upload': [ignore_missing, unicode_safe],
            'clear_search_background_upload': [ignore_missing, unicode_safe],
            'template_file': [ignore_missing, unicode_safe],
            'template_file_upload': [ignore_missing, unicode_safe],
            'clear_template_file_upload': [ignore_missing, unicode_safe],
            'import_org': [ignore_missing, unicode_safe],
            'import_log': [ignore_missing, unicode_safe],
        })

        return schema

    # IAuthFunctions
    def get_auth_functions(self):
        auth_functions = {
            'member_create': self.member_create
        }
        return auth_functions

    def member_create(self, context, data_dict):
        """
        This code is largely borrowed from /src/ckan/ckan/logic/auth/create.py
        With a modification to allow users to add datasets to any group
        :param context:
        :param data_dict:
        :return:
        """
        group = logic_auth.get_group_object(context, data_dict)
        user = context['user']

        # User must be able to update the group to add a member to it
        permission = 'update'
        # However if the user is member of group then they can add/remove datasets
        if not group.is_organization and data_dict.get('object_type') == 'package':
            permission = 'manage_group'

        if c.controller in ['package', 'dataset'] and c.action in ['groups']:
            authorized = noh.user_has_admin_access(include_editor_access=True)
            # Fallback to the default CKAN behaviour
            if not authorized:
                authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                        user,
                                                                        permission)
        else:
            authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                    user,
                                                                    permission)
        if not authorized:
            return {'success': False,
                    'msg': _('User %s not authorized to edit group %s') %
                           (str(user), group.id)}
        else:
            return {'success': True}
    
    def before_view(self, pkg_dict):
        pkg_dict = logic.get_action("package_show")({}, {
            'include_tracking': True,
            'id': pkg_dict['id']
        })
        return pkg_dict
    
    def before_search(self, search_params):
        if 'q' in search_params:
            q = search_params['q']
            if ":" not in q:
                q = 'text:*'+q+'*'
            search_params['q'] = q
        return search_params
    
    def create(self, package):
        self.modify_package_before(package)
    
    def edit(self, package):
        self.modify_package_before(package)
    
    def modify_package_before(self, package):
        package.state = 'active'
        
    def get_validators(self):
        return {
            'tag_name_validator': tag_name_validator,
            'tag_length_validator': tag_length_validator,
            'tag_string_convert': tag_string_convert,
        }
    
    def get_helpers(self):
        return {
            'thai_gdc_get_organizations': noh.get_organizations,
            'thai_gdc_get_groups': noh.get_groups,
            'thai_gdc_get_resource_download': noh.get_resource_download,
            'thai_gdc_day_thai': noh.day_thai,
            'thai_gdc_get_stat_all_view': noh.get_stat_all_view,
            'thai_gdc_get_last_update_tracking': noh.get_last_update_tracking,
            'thai_gdc_facet_chart': noh.facet_chart,
            'thai_gdc_get_page': noh.get_page,
            'thai_gdc_get_recent_view_for_package': noh.get_recent_view_for_package,
            'thai_gdc_get_featured_pages': noh.get_featured_pages,
            'thai_gdc_get_all_groups': noh.get_all_groups,
            'thai_gdc_get_all_groups_all_type': noh.get_all_groups_all_type
        }

class Invalid(Exception):
    pass

def tag_name_validator(value, context):
    tagname_match = re.compile('[\w \-.]*$', re.UNICODE)
    #if not tagname_match.match(value):
    if isinstance(value, str):
        value = value.decode('utf8')
    if not tagname_match.match(value, re.U):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: -_.') % (value))
    return value

def tag_length_validator(value, context):
    if isinstance(value, str):
        value = value.decode('utf8')
    if len(value) < MIN_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is less than minimum %s') % (value, MIN_TAG_LENGTH)
        )
    if len(value) > MAX_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is more than maximum %i') % (value, MAX_TAG_LENGTH)
        )
    return value

def tag_string_convert(key, data, errors, context):
    '''Takes a list of tags that is a comma-separated string (in data[key])
    and parses tag names. These are added to the data dict, enumerated. They
    are also validated.'''

    if isinstance(data[key], string_types):
        tags = [tag.strip() \
                for tag in data[key].split(',') \
                if tag.strip()]
    else:
        tags = data[key]

    current_index = max( [int(k[1]) for k in data.keys() if len(k) == 3 and k[0] == 'tags'] + [-1] )

    for num, tag in zip(count(current_index+1), tags):
        data[('tags', num, 'name')] = tag

    for tag in tags:
        tag_length_validator(tag, context)
        tag_name_validator(tag, context)