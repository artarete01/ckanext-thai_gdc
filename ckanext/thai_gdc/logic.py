#!/usr/bin/env python
# encoding: utf-8

import ckan.logic as logic
import ckan.logic.action.update as logic_action_update
import ckan.model as model
import logging
import ckan.plugins.toolkit as toolkit
from ckanext.thai_gdc.controllers.dataset import DatasetImportController
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
import ckan.lib.dictization.model_dictize as model_dictize
from six import string_types
import ckan.model.misc as misc
from ckan.common import config

_check_access = logic.check_access
_get_or_bust = logic.get_or_bust
NotFound = logic.NotFound

log = logging.getLogger(__name__)

def group_type_patch(context, data_dict):
    _check_access('sysadmin', context, data_dict)
    group_id = _get_or_bust(data_dict, 'name')
    group_type = _get_or_bust(data_dict, 'type')
    catalog_org_type = config.get('thai_gdc.catalog_org_type', 'agency')
    if catalog_org_type == 'area_based':
        model.Session.query(model.Group).filter(model.Group.name == group_id).filter(model.Group.state == 'active').filter(model.Group.is_organization == False).update({"type": group_type})
        model.Session.commit()
        return 'success'
    return

def _tag_search(context, data_dict):
    model = context['model']

    terms = data_dict.get('query') or data_dict.get('q') or []
    if isinstance(terms, string_types):
        terms = [terms]
    terms = [t.strip() for t in terms if t.strip()]

    if 'fields' in data_dict:
        log.warning('"fields" parameter is deprecated.  '
                    'Use the "query" parameter instead')

    fields = data_dict.get('fields', {})
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)

    if 'vocabulary_id' in data_dict:
        # Filter by vocabulary.
        vocab = model.Vocabulary.get(_get_or_bust(data_dict, 'vocabulary_id'))
        if not vocab:
            raise NotFound
        q = q.filter(model.Tag.vocabulary_id == vocab.id)
    else:
        # If no vocabulary_name in data dict then show free tags only.
        q = q.filter(model.Tag.vocabulary_id == None)
        # If we're searching free tags, limit results to tags that are
        # currently applied to a package.
        q = q.distinct().join(model.Tag.package_tags)

    for field, value in fields.items():
        if field in ('tag', 'tags'):
            terms.append(value)

    if not len(terms):
        return [], 0

    for term in terms:
        escaped_term = misc.escape_sql_like_special_characters(
            term, escape='\\')
        q = q.filter(model.Tag.name.ilike('%' + escaped_term + '%'))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    return q.all(), count

@logic.side_effect_free
def tag_list(context, data_dict):

    model = context['model']

    vocab_id_or_name = data_dict.get('vocabulary_id')
    query = data_dict.get('query') or data_dict.get('q')
    if query:
        query = query.strip()
    all_fields = data_dict.get('all_fields', None)

    _check_access('tag_list', context, data_dict)

    if query:
        tags, count = _tag_search(context, data_dict)
    else:
        #tags = model.Tag.all(vocab_id_or_name)
        tags = None

    if tags:
        if all_fields:
            tag_list = model_dictize.tag_list_dictize(tags, context)
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list

def bulk_update_public(context, data_dict):
    from ckan.lib.search import rebuild

    _check_access('bulk_update_public', context, data_dict)
    for dataset in data_dict['datasets']:
        model.Session.query(model.PackageExtra).filter(model.PackageExtra.package_id == dataset).filter(model.PackageExtra.key == 'allow_harvest').update({"value": "True"})
    model.Session.commit()
    [rebuild(package_id) for package_id in data_dict['datasets']]
    logic_action_update._bulk_update_dataset(context, data_dict, {'private': False})

def dataset_bulk_import(context, data_dict):
    _check_access('package_create', context, data_dict)
    import_uuid = _get_or_bust(data_dict, 'import_uuid')
    queue = DEFAULT_QUEUE_NAME
    dataset_import = DatasetImportController()
    
    toolkit.enqueue_job(dataset_import._record_type_process, [data_dict], title=u'import record package import_id:{}'.format(import_uuid), queue=queue)
                
    toolkit.enqueue_job(dataset_import._stat_type_process, [data_dict], title=u'import stat package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._gis_type_process, [data_dict], title=u'import gis package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._multi_type_process, [data_dict], title=u'import multi package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._other_type_process, [data_dict], title=u'import other package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._finished_process, [data_dict], title=u'import finished import_id:{}'.format(import_uuid), queue=queue)
    