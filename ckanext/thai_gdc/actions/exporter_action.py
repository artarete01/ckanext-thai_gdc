# -*- coding: utf-8 -*-
import uuid
import os
import math
import pandas as pd
import ckan.plugins as p

columns = [
    {
        'field': 'id',
    },
    {
        'field': 'data_type',
    },
    {
        'field': 'title',
    },
    {
        'field': 'organization',
    },
    {
        'field': 'maintainer',
    },
    {
        'field': 'maintainer_email',
    },
    {
        'field': 'tags',
    },
    {
        'field': 'objective',
    },
    {
        'field': 'update_frequency_unit',
    },
    {
        'field': 'update_frequency_interval',
    },
    {
        'field': 'geo_coverage',
    },
    {
        'field': 'data_source',
    },
    {
        'field': 'data_format',
    },
    {
        'field': 'data_category',
    },
    {
        'field': 'license_id',
    },
    {
        'field': 'accessible_condition',
    },
    {
        'field': 'url',
    },
    {
        'field': 'data_support',
        'allow_type': ['ข้อมูลระเบียน', 'ข้อมูลหลากหลายประเภท', 'ข้อมูลประเภทอื่นๆ'],
    },
    {
        'field': 'data_collect',
        'allow_type': ['ข้อมูลระเบียน', 'ข้อมูลหลากหลายประเภท', 'ข้อมูลประเภทอื่นๆ'],
    },
    {
        'field': 'data_language',
    },
    {
        'field': 'created_date',
        'allow_type': ['ข้อมูลระเบียน', 'ข้อมูลหลากหลายประเภท', 'ข้อมูลประเภทอื่นๆ'],
    },
    {
        'field': 'last_updated_date',
    },
    {
        'field': 'data_release_calendar',
        'allow_type': ['ข้อมูลสถิติ', 'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'first_year_of_data',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'last_year_of_data',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'disaggregate',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'unit_of_measure',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'unit_of_multiplier',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'calculation_method',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'standard',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'official_statistics',
        'allow_type': ['ข้อมูลสถิติ'],
    },
    {
        'field': 'geographic_data_set',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'equivalent_scale',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'west_bound_longitude',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'east_bound_longitude',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'north_bound_longitude',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'south_bound_longitude',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'positional_accuracy',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'reference_period',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'data_release_date',
        'allow_type': ['ข้อมูลภูมิสารสนเทศเชิงพื้นที่'],
    },
    {
        'field': 'high_value_dataset',
        'allow_type': ['ข้อมูลระเบียน', 'ข้อมูลหลากหลายประเภท', 'ข้อมูลประเภทอื่นๆ'],
    },
    {
        'field': 'reference_data',
        'allow_type': ['ข้อมูลระเบียน', 'ข้อมูลหลากหลายประเภท', 'ข้อมูลประเภทอื่นๆ'],
    },
]


def __value_format(field, value):
    if field == 'tags':
        return ','.join([t['display_name'] for t in value])
    elif field == 'organization':
        return value['title']
    elif field in ['data_language', 'data_format', 'objective', 'disaggregate', 'resource_disaggregate']:
        return ','.join(value)
    else:
        return value


def __get_file(results, id):
    my_path = p.toolkit.config.get('ckan.storage_path', None)
    if not my_path:
        raise p.toolkit.ObjectNotFound()

    export_parth = '%s/storage/uploads/admin_export' % my_path
    if not os.path.isdir(export_parth):
        os.mkdir(export_parth)

    file_id = id if id is not None else unicode(uuid.uuid4())
    file_name = '%s/%s' % (export_parth, file_id)

    rec_sheet_name = u'ข้อมูลระเบียน'
    sta_sheet_name = u'ข้อมูลสถิติ'
    gis_sheet_name = u'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'
    oth_sheet_name = u'ข้อมูลประเภทอื่นๆ'
    mlt_sheet_name = u'ข้อมูลหลากหลายประเภท'

    data_set = []
    for data_dict in results:
        data_type = data_dict['data_type'] if 'data_type' in data_dict.keys() else 'ไม่ระบุ'
        find_fields = filter(lambda c: 'allow_type' not in c.keys() or data_type in c['allow_type'], columns)
        type_fields = map(lambda c: c['field'], find_fields)

        row_dict = {'sheet_name': data_type}
        for field in type_fields:
            value = __value_format(field, data_dict[field]) if field in data_dict.keys() else ''
            row_dict.update({field: value})

        data_set.append(row_dict)

    data_set_record = filter(lambda ele: ele['sheet_name'] == rec_sheet_name, data_set)
    df_record = pd.DataFrame.from_dict(data_set_record, orient='columns')

    data_set_stat = filter(lambda ele: ele['sheet_name'] == sta_sheet_name, data_set)
    df_stat = pd.DataFrame.from_dict(data_set_stat, orient='columns')

    data_set_gis = filter(lambda ele: ele['sheet_name'] == gis_sheet_name, data_set)
    df_gis = pd.DataFrame.from_dict(data_set_gis, orient='columns')

    data_set_other = filter(lambda ele: ele['sheet_name'] == oth_sheet_name, data_set)
    df_other = pd.DataFrame.from_dict(data_set_other, orient='columns')

    data_set_multi = filter(lambda ele: ele['sheet_name'] == mlt_sheet_name, data_set)
    df_multi = pd.DataFrame.from_dict(data_set_multi, orient='columns')

    rec_csv = '%s_rec.csv' % file_name
    if not os.path.isfile(rec_csv):
        df_record.to_csv(rec_csv, na_rep='', encoding='utf-8-sig', index=False)
    else:
        df_record.to_csv(rec_csv,
                         na_rep='',
                         encoding='utf-8-sig',
                         index=False,
                         mode='a',
                         header=False)

    sta_csv = '%s_sta.csv' % file_name
    if not os.path.isfile(sta_csv):
        df_stat.to_csv(sta_csv, na_rep='', encoding='utf-8-sig', index=False)
    else:
        df_stat.to_csv(sta_csv,
                       na_rep='',
                       encoding='utf-8-sig',
                       index=False,
                       mode='a',
                       header=False)

    gis_csv = '%s_gis.csv' % file_name
    if not os.path.isfile(gis_csv):
        df_gis.to_csv(gis_csv, na_rep='', encoding='utf-8-sig', index=False)
    else:
        df_gis.to_csv(gis_csv,
                      na_rep='',
                      encoding='utf-8-sig',
                      index=False,
                      mode='a',
                      header=False)

    oth_csv = '%s_oth.csv' % file_name
    if not os.path.isfile(oth_csv):
        df_other.to_csv(oth_csv, na_rep='', encoding='utf-8-sig', index=False)
    else:
        df_other.to_csv(oth_csv,
                        na_rep='',
                        encoding='utf-8-sig',
                        index=False,
                        mode='a',
                        header=False)

    mlt_csv = '%s_mlt.csv' % file_name
    if not os.path.isfile(mlt_csv):
        df_multi.to_csv(mlt_csv, na_rep='', encoding='utf-8-sig', index=False)
    else:
        df_multi.to_csv(mlt_csv,
                        na_rep='',
                        encoding='utf-8-sig',
                        index=False,
                        mode='a',
                        header=False)

    return file_id


@p.toolkit.side_effect_free
def package(context, data_dict):
    p.toolkit.check_access('config_option_update', context, {})
    rows = 100
    page = data_dict.get('p', 1)
    id = data_dict.get('id', None)
    page = int(page)
    start = (page - 1) * rows

    # try:
    pkg = p.toolkit.get_action('package_search')(data_dict={
        'facet': False,
        'include_private': True,
        'rows': rows,
        'start': start
    })
    total = float(pkg['count'])
    page_count = int(math.ceil(total / rows))

    if page > page_count:
        raise p.toolkit.ObjectNotFound()

    file_id = __get_file(pkg['results'], id)

    return {
        'count': total,
        'page': page,
        'page_count': page_count,
        'file_id': file_id
    }


# except:
#    raise p.toolkit.ObjectNotFound()
