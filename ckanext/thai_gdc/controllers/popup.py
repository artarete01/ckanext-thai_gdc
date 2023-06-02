import ckan.plugins as p
import ckan.lib.helpers as h
from ckan.plugins.toolkit import _
import ckan.lib.uploader as uploader


class PopupController(p.toolkit.BaseController):

    def index(self, data=None, errors=None, error_summary=None):
        is_access = h.check_access('config_option_update')
        if not is_access:
            p.toolkit.abort(404, _('Page Not Found'))

        if p.toolkit.request.method == 'POST' and not data:
            data = dict(p.toolkit.request.POST)
            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data, 'EVENT_IMAGE', 'EVENT_IMAGE_UPLOAD', 'EVENT_IMAGE_CLEAR')
            upload.upload(uploader.get_max_image_size())

            data_dict_event = {
                'fields': {
                    'EVENT_IMAGE': data['EVENT_IMAGE'],
                    'EVENT_TEXT': data['EVENT_TEXT'],
                    'EVENT_URL': data['EVENT_URL'],
                    'EVENT_PUBLIC': data['EVENT_PUBLIC']
                },
                'conf_group': 'EVENT'
            }
            try:
                p.toolkit.get_action('gdc_agency_update_conf_group')(data_dict=data_dict_event)
            except p.toolkit.ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.index(data, errors, error_summary)

        if data is None:
            data = p.toolkit.get_action('gdc_agency_get_conf_group')(data_dict={'conf_group': 'EVENT'})

        data.update({
            'EVENT_IMAGE_IS_URL': data and 'EVENT_IMAGE' in data.keys() and data['EVENT_IMAGE'].startswith('http')
        })

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        return p.toolkit.render('admin/popup.html', extra_vars=extra_vars)
