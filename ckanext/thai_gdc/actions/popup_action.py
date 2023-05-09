import ckan.plugins as p
import ckan.lib.navl.dictization_functions as df
import ckanext.thai_gdc.model.popup_model as pop_obj

event_schema = {
    'EVENT_IMAGE': [p.toolkit.get_validator('ignore_missing'), unicode],
    'EVENT_TEXT': [p.toolkit.get_validator('not_empty'), unicode],
    'EVENT_URL': [p.toolkit.get_validator('ignore_missing'), unicode],
    'EVENT_PUBLIC': [p.toolkit.get_validator('not_empty'), unicode],
}


@p.toolkit.side_effect_free
def get_conf_group(context, data_dict):
    conf_group = p.toolkit.get_or_bust(data_dict, 'conf_group')
    out = pop_obj.GdcConfigs.get_group(conf_group=conf_group)
    out_dict = {}
    for pg in out:
        out_dict.update({pg.conf_key: pg.conf_value})

    return out_dict


def update_conf_group(context, data_dict):
    p.toolkit.check_access('config_option_update', context, {})
    fields = p.toolkit.get_or_bust(data_dict, 'fields')
    conf_group = p.toolkit.get_or_bust(data_dict, 'conf_group')

    data, errors = df.validate(fields, event_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    session = context['session']
    for (conf_key, conf_value) in data.items():

        out = pop_obj.GdcConfigs.get(conf_key=conf_key)

        if not out:
            out = pop_obj.GdcConfigs()
            out.conf_key = conf_key

        out.conf_value = conf_value
        out.conf_group = conf_group
        session.add(out)

    session.commit()

