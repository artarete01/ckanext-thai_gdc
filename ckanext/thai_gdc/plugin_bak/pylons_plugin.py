# -*- coding: utf-8 -*-

import ckan.plugins as p


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # IRoutes
    def before_map(self, map):
        map.connect(
            'banner_edit',
            '/ckan-admin/banner-edit',
            action='edit_banner',
            ckan_icon='wrench',
            controller='ckanext.thai_gdc.controllers.banner:BannerEditController',
            )
        map.connect(
            'dataset_import',
            '/ckan-admin/dataset-import',
            action='import_dataset',
            ckan_icon='cloud-upload',
            controller='ckanext.thai_gdc.controllers.dataset:DatasetImportController',
            )
        map.connect(
            'clear_import_log',
            '/ckan-admin/clear-import-log',
            action='clear_import_log',
            controller='ckanext.thai_gdc.controllers.dataset:DatasetImportController',
            )
        map.connect(
            'dataset_datatype_patch',
            '/dataset/edit-datatype/{package_id}',
            action='datatype_patch',
            controller='ckanext.thai_gdc.controllers.dataset:DatasetManageController',
            )
        map.connect(
            'user_active',
            '/user/edit/user_active',
            action='user_active',
            controller='ckanext.thai_gdc.controllers.user:UserManageController',
            )

        return map