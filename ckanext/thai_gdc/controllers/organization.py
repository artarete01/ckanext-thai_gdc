# encoding: utf-8

import logging
import re

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
import ckan.lib.plugins as lib_plugins
import ckan.plugins as plugins
from ckan.plugins.toolkit import (
    _, c, BaseController, check_access, NotAuthorized, abort, render,
    redirect_to, request,
    )
from ckan.common import g, config, _
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action

log = logging.getLogger(__name__)

lookup_group_plugin = lib_plugins.lookup_group_plugin

is_org = True

def _get_group_template(template_type, group_type=None):
    group_plugin = lookup_group_plugin(group_type)
    method = getattr(group_plugin, template_type)
    try:
        return method(group_type)
    except TypeError as err:
        if u'takes 1' not in str(err) and u'takes exactly 1' not in str(err):
            raise
        return method()

def _replace_group_org(string):
    u''' substitute organization for group if this is an org'''
    if is_org:
        return re.sub(u'^group', u'organization', string)
    return string

def _action(action_name):
    u''' select the correct group/org action '''
    return get_action(_replace_group_org(action_name))

def _check_access(action_name, *args, **kw):
    u''' select the correct group/org check_access '''
    return check_access(_replace_group_org(action_name), *args, **kw)

class OrganizationCustomController(plugins.toolkit.BaseController):
    def index(self):
        group_type = 'organization'
        is_organization = True
        extra_vars = {}
        page = h.get_page_number(request.params) or 1
        items_per_page = int(config.get(u'ckan.datasets_per_page', 20))

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'for_view': True,
            u'with_private': False
        }

        try:
            _check_access(u'site_read', context)
            _check_access(u'group_list', context)
        except NotAuthorized:
            base.abort(403, _(u'Not authorized to see this page'))

        q = request.params.get(u'q', u'')
        if q=='':
            extra_vars["page"] = h.Page([], 0)
            extra_vars["group_type"] = group_type
            return base.render(
                _get_group_template(u'index_template', group_type), extra_vars)
        sort_by = request.params.get(u'sort')

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.q = q
        g.sort_by_selected = sort_by

        extra_vars["q"] = q
        extra_vars["sort_by_selected"] = sort_by

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if g.userobj:
            context['user_id'] = g.userobj.id
            context['user_is_admin'] = g.userobj.sysadmin

        try:
            data_dict_global_results = {
                u'all_fields': False,
                u'q': q,
                u'sort': sort_by,
                u'type': group_type or u'group',
            }
            global_results = _action(u'group_list')(context,
                                                    data_dict_global_results)
        except ValidationError as e:
            if e.error_dict and e.error_dict.get(u'message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            h.flash_error(msg)
            extra_vars["page"] = h.Page([], 0)
            extra_vars["group_type"] = group_type
            return base.render(
                _get_group_template(u'index_template', group_type), extra_vars)

        data_dict_page_results = {
            u'all_fields': True,
            u'q': q,
            u'sort': sort_by,
            u'type': group_type or u'group',
            u'limit': items_per_page,
            u'offset': items_per_page * (page - 1),
            u'include_extras': True
        }
        page_results = _action(u'group_list')(context, data_dict_page_results)

        extra_vars["page"] = h.Page(
            collection=global_results,
            page=page,
            url=h.pager_url,
            items_per_page=items_per_page, )

        extra_vars["page"].items = page_results
        extra_vars["group_type"] = group_type

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.page = extra_vars["page"]
        return base.render(
            _get_group_template(u'index_template', group_type), extra_vars)
