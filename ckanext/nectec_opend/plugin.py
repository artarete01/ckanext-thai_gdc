# -*- coding: utf-8 -*-

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import re
from itertools import count
from six import string_types
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH)
from ckan.lib.helpers import json

import logging

log = logging.getLogger(__name__)

class Nectec_OpendPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IValidators)


    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'nectec_opend')
    
    def before_search(self, search_params):
        if 'q' in search_params:
            q = search_params['q']
            if ":" not in q:
                q = 'text:*'+q+'*'
            search_params['q'] = q
        return search_params
    
    def after_create(self, context, data_dict):
        if 'state' in data_dict and data_dict['state'] == 'draft':
            data_dict['state'] = 'active'
            toolkit.get_action('package_update')(context, data_dict)
    
    def after_update(self, context, data_dict):
        if 'state' in data_dict and data_dict['state'] == 'draft':
            data_dict['state'] = 'active'
            toolkit.get_action('package_update')(context, data_dict)
    
    def get_validators(self):
        return {
            'tag_name_validator': tag_name_validator,
            'tag_length_validator': tag_length_validator,
            'tag_string_convert': tag_string_convert,
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