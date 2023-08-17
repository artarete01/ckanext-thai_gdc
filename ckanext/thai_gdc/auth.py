#!/usr/bin/env python
# encoding: utf-8

import ckan.plugins.toolkit as toolkit
from ckan.common import _, c
import ckan.logic.auth as logic_auth
from ckan import logic
import ckan.authz as authz
from ckanext.thai_gdc import helpers as thai_gdc_h

import logging

log = logging.getLogger(__name__)

@toolkit.auth_allow_anonymous_access
def resource_show(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}

    res_private = data_dict.get('resource_private','')

    if res_private == "True" and not authz.is_authorized('package_update', context, pkg_dict).get('success'):
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}

    authorized = authz.is_authorized('package_show', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}
    else:
        return {'success': True}

def member_create(context, data_dict):
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
        authorized = thai_gdc_h.user_has_admin_access(include_editor_access=True)
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
    
def user_generate_apikey( context, data_dict):
    user = context['user']
    user_obj = logic_auth.get_user_object(context, data_dict)
    # if user == user_obj.name:
    #     # Allow users to update only their own user accounts.
    #     return {'success': True}
    return {'success': False, 'msg': _('User {0} not authorized to update user'
            ' {1}'.format(user, user_obj.id))}

def package_delete(context, data_dict):
    # Defer authorization for package_delete to package_update, as deletions
    # are essentially changing the state field
    try:
        gd_pkg_state = thai_gdc_h.get_gdcatalog_state('published', data_dict.get('id')).get('result')
        if gd_pkg_state[0].get('metadata_modified') != '' and toolkit.c.controller == 'dataset':
            return {'success': False}
        else:
            return authz.is_authorized('package_update', context, data_dict)
    except:
        return {'success': False}

def resource_delete(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete resource %s') % (user, resource.id)}
    else:
        return {'success': True}