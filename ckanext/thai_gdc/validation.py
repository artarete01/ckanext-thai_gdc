#!/usr/bin/env python
# encoding: utf-8

import re
from itertools import count
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH, PACKAGE_NAME_MIN_LENGTH)
from ckan.model.core import State
from six import string_types
import ckan.lib.navl.dictization_functions as df
from ckan.common import _

Invalid = df.Invalid
missing = df.missing

def tag_name_validator(value, context):

    tagname_match = re.compile('[ก-๙\w \-.]*', re.UNICODE)
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
    
    if not len(tags):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: -_.') % (''))

    current_index = max( [int(k[1]) for k in data.keys() if len(k) == 3 and k[0] == 'tags'] + [-1] )

    for num, tag in zip(count(current_index+1), tags):
        data[('tags', num, 'name')] = tag

    for tag in tags:
        tag_length_validator(tag, context)
        tag_name_validator(tag, context)
    
def package_name_validator(key, data, errors, context):
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.state).filter_by(name=data[key])
    if package:
        package_id = package.id
    else:
        package_id = data.get(key[:-1] + ('id',))
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)
    result = query.first()
    if result and result.state != State.DELETED:
        errors[key].append(_('That URL is already in use.'))
    elif result and result.state == State.DELETED:
        errors[key].append(_('That URL is already in trash.'))

    value = data[key]
    if len(value) < PACKAGE_NAME_MIN_LENGTH:
        raise Invalid(
            _('Name "%s" length is less than minimum %s') % (value, PACKAGE_NAME_MIN_LENGTH)
        )
    if len(value) > 70:
        raise Invalid(
            _('Name "%s" length is more than maximum %s') % (value, 70)
        )
    
def package_title_validator(key, data, errors, context):
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.state).filter_by(title=data[key]).filter_by(type='dataset')
    if package:
        package_id = package.id
    else:
        package_id = data.get(key[:-1] + ('id',))
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)
    result = query.first()
    if result and result.state != State.DELETED:
        errors[key].append(_('That title is already in use.'))