#!/usr/bin/env python
# encoding: utf-8

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, c
import ckan.lib.helpers as h
import ckan.lib.formatters as formatters
import json
import collections
from ckan.lib.search import make_connection
import logging
from ckanapi import LocalCKAN, NotFound, NotAuthorized

from ckanext.dundee.dundee_model.dundee_model import DundeeModel

get_action = logic.get_action
dundee_model = DundeeModel()

log = logging.getLogger(__name__)

def get_stat_all_view():
    return 1

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
