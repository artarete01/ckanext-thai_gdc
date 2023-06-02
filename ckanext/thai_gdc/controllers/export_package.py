# -*- coding: utf-8 -*-
import os
import ckan.plugins as p
import ckan.lib.helpers as h
from ckan.plugins.toolkit import _

import paste.fileapp
import pandas as pd


class ExportPackageController(p.toolkit.BaseController):

    def __init__(self):
        my_path = p.toolkit.config.get('ckan.storage_path', None)
        if not my_path:
            p.toolkit.abort(404, _('Page Not Found'))

        self.export_path = '%s/storage/uploads/admin_export' % my_path

    def index(self):

        is_access = h.check_access('config_option_update')
        if not is_access:
            p.toolkit.abort(404, _('Page Not Found'))

        if os.path.isdir(self.export_path):
            for filename in os.listdir(self.export_path):
                file_path = os.path.join(self.export_path, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        return p.toolkit.render('admin/export_package.html')

    def download(self, id=None):
        is_access = h.check_access('config_option_update')
        if not is_access:
            p.toolkit.abort(404, _('Page Not Found'))

        if id is None:
            p.toolkit.abort(404, _('Page Not Found'))

        file_path = '%s/%s.xlsx' % (self.export_path, id)
        rec_sheet_name = u'ข้อมูลระเบียน'
        sta_sheet_name = u'ข้อมูลสถิติ'
        gis_sheet_name = u'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'
        oth_sheet_name = u'ข้อมูลประเภทอื่นๆ'
        mlt_sheet_name = u'ข้อมูลหลากหลายประเภท'

        with pd.ExcelWriter(file_path) as writer:
            rec_csv = '%s/%s_rec.csv' % (self.export_path, id)
            if os.path.isfile(rec_csv):
                try:
                    df_record = pd.read_csv(rec_csv, keep_default_na=False, error_bad_lines=False)
                    df_record.to_excel(writer, encoding='utf-8', sheet_name=rec_sheet_name)
                except:
                    pass
                os.unlink(rec_csv)

            sta_csv = '%s/%s_sta.csv' % (self.export_path, id)
            if os.path.isfile(sta_csv):
                try:
                    df_stat = pd.read_csv(sta_csv, keep_default_na=False, error_bad_lines=False)
                    df_stat.to_excel(writer, encoding='utf-8', sheet_name=sta_sheet_name)
                except:
                    pass
                os.unlink(sta_csv)

            gis_csv = '%s/%s_gis.csv' % (self.export_path, id)
            if os.path.isfile(gis_csv):
                try:
                    df_gis = pd.read_csv(gis_csv, keep_default_na=False, error_bad_lines=False)
                    df_gis.to_excel(writer, encoding='utf-8', sheet_name=gis_sheet_name)
                except:
                    pass
                os.unlink(gis_csv)

            oth_csv = '%s/%s_oth.csv' % (self.export_path, id)
            if os.path.isfile(oth_csv):
                try:
                    df_other = pd.read_csv(oth_csv, keep_default_na=False, error_bad_lines=False)
                    df_other.to_excel(writer, encoding='utf-8', sheet_name=oth_sheet_name)
                except:
                    pass
                os.unlink(oth_csv)

            mlt_csv = '%s/%s_mlt.csv' % (self.export_path, id)
            if os.path.isfile(mlt_csv):
                try:
                    df_multi = pd.read_csv(mlt_csv, keep_default_na=False, error_bad_lines=False)
                    df_multi.to_excel(writer, encoding='utf-8', sheet_name=mlt_sheet_name)
                except:
                    pass
                os.unlink(mlt_csv)

        if not os.path.exists(file_path):
            p.toolkit.abort(404, _('Page Not Found'))

        fileapp = paste.fileapp.FileApp(file_path)

        try:
            status, headers, app_iter = p.toolkit.request.call_application(fileapp)
        except OSError:
            p.toolkit.abort(404, _('Resource data not found'))

        os.unlink(file_path)
        p.toolkit.response.content_type = 'application/application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        p.toolkit.response.headers['Content-disposition'] = 'attachment; filename=dataset.xlsx'
        return app_iter
