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
from ckan.lib.helpers import json
from ckanext.thai_gdc import helpers as noh
from ckanext.pages.interfaces import IPagesSchema

import logging

log = logging.getLogger(__name__)

class Thai_GDCPlugin(plugins.SingletonPlugin, DefaultTranslation, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(IPagesSchema)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'thai_gdc')
    
    def before_map(self, map):
        opend_controller = 'ckanext.thai_gdc.controllers.opend:OpendController'

        return map

    def update_config_schema(self, schema):

        ignore_missing = toolkit.get_validator('ignore_missing')
        remove_whitespace = toolkit.get_validator('remove_whitespace')

        schema.update({
            'ckan.promoted_banner': [ignore_missing, unicode, remove_whitespace],
            'ckan.site_org_address': [ignore_missing, unicode],
            'ckan.site_org_contact': [ignore_missing, unicode],
            'ckan.site_org_email': [ignore_missing, unicode],
            'ckan.site_policy_link': [ignore_missing, unicode],
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

    #IPagesSchema 
    def update_pages_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        boolean_validator = toolkit.get_validator('boolean_validator')

        schema.update({
            'featured': [ignore_missing, boolean_validator],
        })

        return schema
    
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
            'thai_gdc_facet_chart': noh.facet_chart,
            'thai_gdc_get_page': noh.get_page,
            'thai_gdc_get_recent_view_for_package': noh.get_recent_view_for_package,
            'thai_gdc_get_featured_pages': noh.get_featured_pages,
            'thai_gdc_get_all_groups': noh.get_all_groups,
            'thai_gdc_get_all_groups_all_type': noh.get_all_groups_all_type
        }
        
    
def tag_name_validator(value, context):
    tagname_match = re.compile('[\w \-.]*$', re.UNICODE)
    #if not tagname_match.match(value):
    if not tagname_match.match(value, re.U):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: -_.') % (value))
    return value

def tag_length_validator(value, context):

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