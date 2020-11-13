import ckan.plugins as p
import ckan.lib.helpers as helpers
from pylons import config

_ = p.toolkit._


class OpendController(p.toolkit.BaseController):
    controller = 'ckanext.nectec_opend.controllers.opend:OpendController'

    def page_index(self):
        return self._pages_list_pages('page')
    
    def _pages_list_pages(self, page_type):
        data_dict={'org_id': None, 'page_type': page_type}
        p.toolkit.c.pages_dict = p.toolkit.get_action('ckanext_pages_list')(
            data_dict=data_dict
        )
        p.toolkit.c.page = helpers.Page(
            collection=p.toolkit.c.pages_dict,
            page=p.toolkit.request.params.get('page', 1),
            url=helpers.pager_url,
            items_per_page=21
        )

        return p.toolkit.render('ckanext_pages/pages_list.html')