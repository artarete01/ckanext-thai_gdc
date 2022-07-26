#!/usr/bin/env python
# encoding: utf-8

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from pylons import config
from ckan.common import _, c
import ckan.lib.helpers as h
import json
import os
import logging
import ckan.lib.dictization.model_dictize as model_dictize

from ckanext.thai_gdc.model.opend import OpendModel
import requests
from datetime import datetime as dt

get_action = logic.get_action
opend_model = OpendModel()

log = logging.getLogger(__name__)

def dataset_bulk_import_log(import_id):
    logs = opend_model.get_dataset_bulk_import_log(import_id)
    return logs

def dataset_bulk_import_status(import_id):
    try:
        context = {'model': model,
                    'user': c.user, 'auth_user_obj': c.userobj}

        like_q1 = u'%' + import_id + u'%'
        like_q2 = u'%Finished%'

        q = model.Session.query(model.Activity).filter(model.Activity.activity_type == 'changed user').filter(model.Activity.data.ilike(like_q1)).filter(model.Activity.data.ilike(like_q2))
        activities = q.all()
    except:
        return []

    return model_dictize.activity_list_dictize(
        activities, context,
        include_data=True)

def dataset_bulk_import_count(log_contents):
    complete = 0
    for log_item in log_contents:
        complete = complete + log_item['log_content'].count('package_create')
    return complete

def get_group_color(group_id):

    first_char = group_id[0]

    color = {
        '0': 'firebrick',
        '1': 'darkorange',
        '2': 'darkkhaki',
        '3': 'olivedrab',
        '4': 'teal',
        '5': 'royalblue',
        '6': 'slateblue',
        '7': 'purple',
        '8': 'mediumvioletred',
        '9': 'darkslategray',
        'a': 'saddlebrown',
        'b': 'green',
        'c': 'firebrick',
        'd': 'darkorange',
        'e': 'darkkhaki',
        'f': 'olivedrab',
        'g': 'teal',
        'h': 'royalblue',
        'i': 'slateblue',
        'j': 'purple',
        'k': 'mediumvioletred',
        'l': 'darkslategray',
        'm': 'saddlebrown',
        'n': 'green',
        'o': 'firebrick',
        'p': 'darkorange',
        'q': 'darkkhaki',
        'r': 'olivedrab',
        's': 'teal',
        't': 'royalblue',
        'u': 'slateblue',
        'v': 'purple',
        'w': 'mediumvioletred',
        'x': 'darkslategray',
        'y': 'saddlebrown',
        'z': 'green'
    }

    return first_char in color and color[first_char] or 'gray'

def get_site_statistics():
    stats = {}
    stats['dataset_count'] = logic.get_action('package_search')(
        {}, {"rows": 1,"include_private":True})['count']
    if config.get('scheming.group_schemas', '') != '':
        query = model.Session.query(model.Group) \
            .filter(model.Group.state == 'active') \
            .filter(model.Group.type != 'organization') \
            .filter(model.Group.type != 'group')
    
        resultproxy = model.Session.execute(query).fetchall()
        stats['group_count'] = len(resultproxy)
    else:
        stats['group_count'] = len(logic.get_action('group_list')({}, {}))

    stats['organization_count'] = len(
        logic.get_action('organization_list')({}, {}))
    return stats

def convert_string_todate(str_date, format):
    return dt.strptime(str_date, format)

def get_opend_playground_url():
    return config.get('thai_gdc.opend_playground_url')

def get_catalog_org_type():
    return config.get('thai_gdc.catalog_org_type', 'agency')

def get_is_as_a_service():
    return config.get('thai_gdc.is_as_a_service', 'false')

def get_gdcatalog_status_show():
    return config.get('thai_gdc.gdcatalog_status_show')

def get_gdcatalog_portal_url():
    return config.get('thai_gdc.gdcatalog_portal_url')

def get_gdcatalog_version_update():
    gdcatalog_harvester_url = config.get('thai_gdc.gdcatalog_harvester_url')
    request_proxy = config.get('thai_gdc.proxy_request', None)
    if request_proxy:
        proxies = {
            'http': config.get('thai_gdc.proxy_url', None),
            'https': config.get('thai_gdc.proxy_url', None)
        }
    else:
        proxies = None

    state = 'connection error'
    gdcatalog_version = 'gdcatalog'
    local_version = 'local'
    try:
        with requests.Session() as s:
            s.verify = False
            url = gdcatalog_harvester_url+'/base/admin/thai-gdc-update.json'
            headers = {'Content-type': 'application/json', 'Authorization': ''}
            res = s.get(url, headers = headers, proxies=proxies)
            log.info(res.text)
            gdcatalog_version = json.loads(res.text)['version']
            local_version = get_extension_version('version')
        if gdcatalog_version != local_version:
            state = gdcatalog_version
        else:
            state = 'updated'
    except:
        return state
    
    return state

def get_gdcatalog_state(zone, package_id):
    state = []
    gdcatalog_status_show = get_gdcatalog_status_show()
    gdcatalog_harvester_url = config.get('thai_gdc.gdcatalog_harvester_url')
    site_url = config.get('ckan.site_url')
    request_proxy = config.get('thai_gdc.proxy_request', None)
    if request_proxy:
        proxies = {
            'http': config.get('thai_gdc.proxy_url', None),
            'https': config.get('thai_gdc.proxy_url', None)
        }
    else:
        proxies = None
    if gdcatalog_status_show == 'true':
        try:
            with requests.Session() as s:
                s.verify = False
                if zone == 'published':
                    url = gdcatalog_harvester_url+'/api/3/action/gdcatalog_published_state'
                elif zone == 'nonpublish':
                    url = gdcatalog_harvester_url+'/api/3/action/gdcatalog_nonpublish_state'
                myobj = {"site_url": site_url.split("//")[1].split("/")[0], "package": package_id}
                myobj['site_url'] = myobj['site_url'].encode('ascii','ignore')
                myobj['package'] = myobj['package'].encode('ascii','ignore')
                log.info(json.dumps(myobj))
                headers = {'Content-type': 'application/json', 'Authorization': ''}
                res = s.post(url, data = json.dumps(myobj), headers = headers, proxies=proxies)
                log.info(res.json())
                state = res.json()
        except:
            return state
    return state

def get_users_non_member():
    users = opend_model.get_users_non_member()
    return [d['id'] for d in users]

def get_users_deleted():
    query = model.Session.query(model.User.name)
    query = query.filter_by(state='deleted')
    users_list = []
    for user in query.all():
        users_list.append(user[0])
    return users_list

def get_extension_version(attr):
    dirname, filename = os.path.split(os.path.abspath(__file__))
    f = open(dirname+'/public/base/admin/thai-gdc-update.json',) 
    data = json.load(f)
    return data[attr]

def get_action(action_name, data_dict=None):
    '''Calls an action function from a template. Deprecated in CKAN 2.3.'''
    if data_dict is None:
        data_dict = {}
    return logic.get_action(action_name)({}, data_dict)

def get_organizations(all_fields=False, include_dataset_count=False, sort="name asc"):
    context = {'user': c.user}
    data_dict = {
        'all_fields': all_fields,
        'include_dataset_count': include_dataset_count,
        'sort': sort}
    return logic.get_action('organization_list')(context, data_dict)

def get_groups(all_fields=False, include_dataset_count=False, sort="name asc"):
    context = {'user': c.user}
    data_dict = {
        'all_fields': all_fields,
        'include_dataset_count': include_dataset_count,
        'sort': sort}
    return logic.get_action('group_list')(context, data_dict)

def get_resource_download(resource_id):
    return opend_model.get_resource_download(resource_id)

def get_stat_all_view():
    num = opend_model.get_all_view()
    return num

def get_last_update_tracking():
    last_update = opend_model.get_last_update_tracking()
    return last_update

def day_thai(t):
    month = [
        _('January'), _('February'), _('March'), _('April'),
        _('May'), _('June'), _('July'), _('August'),
        _('September'), _('October'), _('November'), _('December')
    ]

    raw = str(t)
    tmp = raw.split(' ')
    dte = tmp[0]

    tmp = dte.split('-')
    m_key = int(tmp[1]) - 1

    if h.lang() == 'th':
        dt = u"{} {} {}".format(int(tmp[2]), month[m_key], int(tmp[0]) + 543)
    else:
        dt = u"{} {}, {}".format(month[m_key], int(tmp[2]), int(tmp[0]))

    return dt

def facet_chart(type, limit):
    items = h.get_facet_items_dict(type, limit)
    i = 1
    data = []
    context = {'model': model}
    for item in items:
        my_dict = {column: value for column, value in item.items()}
        item['rownum'] = i
        if type == 'groups':
            group_dict = logic.get_action('group_show')(context, {'id': item['name']})
            item['image_url'] = group_dict['image_url']
        data.append(item)
        i += 1

    return data

def get_recent_view_for_package(package_id):
    rs = model.TrackingSummary.get_for_package(package_id)
    return rs['recent']

def get_featured_pages(per_page):
    pages = opend_model.get_featured_pages(per_page)
    return pages

def get_page(name):
    #if db.pages_table is None:
    #    db.init_db(model)
    page = opend_model.get_page(name)
    return page

def is_user_sysadmin(user=None):
    """Returns True if authenticated user is sysadmim
    :rtype: boolean
    """
    if user is None:
        user = toolkit.c.userobj
    return user is not None and user.sysadmin


def user_has_admin_access(include_editor_access=False):
    user = toolkit.c.userobj
    # If user is "None" - they are not logged in.
    if user is None:
        return False
    if is_user_sysadmin(user):
        return True

    groups_admin = user.get_groups('organization', 'admin')
    groups_editor = user.get_groups('organization', 'editor') if include_editor_access else []
    groups_list = groups_admin + groups_editor
    organisation_list = [g for g in groups_list if g.type == 'organization']
    return len(organisation_list) > 0

def get_all_groups():
    groups = toolkit.get_action('group_list')(
        data_dict={'include_dataset_count': False, 'all_fields': True})
    pkg_group_ids = set(group['id'] for group
                        in c.pkg_dict.get('groups', []))
    return [[group['id'], group['display_name']]
            for group in groups if
            group['id'] not in pkg_group_ids]

def get_all_groups_all_type(type=None):    
    user_groups = opend_model.get_groups_all_type(type)

    pkg_group_ids = set(group['id'] for group
                            in c.pkg_dict.get('groups', []))
    return [[group['id'], group['display_name']]
                            for group in user_groups if
                            group['id'] not in pkg_group_ids]
