# encoding: utf-8

import logging
import re
from collections import OrderedDict

import six
from six import string_types
from six.moves.urllib.parse import urlencode

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.plugins as plugins
from ckan.plugins.toolkit import (
    _, c, BaseController, check_access, NotAuthorized, abort, render,
    redirect_to, request,
    )
from ckan.common import g, config, _
from ckan.views.home import CACHE_PARAMETERS
from ckan.views.dataset import _get_search_details

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

log = logging.getLogger(__name__)

lookup_group_plugin = lib_plugins.lookup_group_plugin
lookup_group_controller = lib_plugins.lookup_group_controller
lookup_group_blueprint = lib_plugins.lookup_group_blueprints

is_org = False


def _get_group_template(template_type, group_type=None):
    group_plugin = lookup_group_plugin(group_type)
    method = getattr(group_plugin, template_type)
    try:
        return method(group_type)
    except TypeError as err:
        if u'takes 1' not in str(err) and u'takes exactly 1' not in str(err):
            raise
        return method()


def _db_to_form_schema(group_type=None):
    u'''This is an interface to manipulate data from the database
     into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    if u'type' not in data_dict:
        data_dict[u'type'] = group_type
    return lookup_group_plugin(group_type).\
        setup_template_variables(context, data_dict)


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


def _render_template(template_name, group_type):
    u''' render the correct group/org template '''
    return base.render(
        _replace_group_org(template_name),
        extra_vars={u'group_type': group_type})


def _force_reindex(grp):
    u''' When the group name has changed, we need to force a reindex
    of the datasets within the group, otherwise they will stop
    appearing on the read page for the group (as they're connected via
    the group name)'''
    group = model.Group.get(grp['name'])
    for dataset in group.packages():
        search.rebuild(dataset.name)


def _guess_group_type(expecting_name=False):
    u"""
            Guess the type of group from the URL.
            * The default url '/group/xyz' returns None
            * group_type is unicode
            * this handles the case where there is a prefix on the URL
              (such as /data/organization)
        """
    parts = [x for x in request.path.split(u'/') if x]

    idx = 0
    if expecting_name:
        idx = -1

    gt = parts[idx]

    return gt


def set_org(is_organization):
    global is_org
    is_org = is_organization

class OrganizationCustomController(plugins.toolkit.BaseController):
    def index(self):
        group_type = 'organization'
        is_organization = True
        log.info('Patipattttt')
        extra_vars = {}
        set_org(is_organization)
        page = h.get_page_number(request.params) or 1
        items_per_page = int(config.get(u'ckan.datasets_per_page', 20))

        log.info('test route custom')

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
        if q=='': #Patipat add
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
