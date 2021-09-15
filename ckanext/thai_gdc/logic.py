#!/usr/bin/env python
# encoding: utf-8

import ckan.logic as logic
import ckan.logic.action.update as logic_action_update
import ckan.plugins as plugins
import ckan.model as model
import logging
import ckan.plugins.toolkit as toolkit
import ckan.lib.search as search

import pandas as pd
import numpy as np
import re
from ckanapi import LocalCKAN
import datetime
# if not toolkit.check_ckan_version('2.9'):
#     from ckanext.thai_gdc.controllers.dataset import DatasetImportController
from ckan.lib.jobs import DEFAULT_QUEUE_NAME

_check_access = logic.check_access
_get_or_bust = logic.get_or_bust

log = logging.getLogger(__name__)

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
    # dataset_import = DatasetImportController()
    
    toolkit.enqueue_job(_record_type_process, [data_dict], title='import record package import_id:{}'.format(import_uuid), queue=queue)
                
    toolkit.enqueue_job(_stat_type_process, [data_dict], title='import stat package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(_gis_type_process, [data_dict], title='import gis package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(_multi_type_process, [data_dict], title='import multi package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(_other_type_process, [data_dict], title='import other package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(_finished_process, [data_dict], title='import finished import_id:{}'.format(import_uuid), queue=queue)
    
def _record_type_process(data_dict):
    try:
        record_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Record', dtype=str)
        record_df.drop(0, inplace=True)
        record_df["data_type"] = 'ข้อมูลระเบียน'

        record_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        record_df.drop(['d_type'], axis=1, inplace=True)
        record_df = record_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        record_df.replace(np.nan, '', regex=True, inplace=True)

        record_df['high_value_dataset'] = np.where(record_df['high_value_dataset'].str.contains("ไม่"), False, True)
        record_df['reference_data'] = np.where(record_df['reference_data'].str.contains("ไม่"), False, True)

        record_df["dataset_name"] = record_df["name"]
        record_df["name"] = record_df["name"].str.lower()
        record_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            record_df = record_df.loc[record_df['owner_org'] == data_dict['template_org']]
            record_df.reset_index(drop=True, inplace=True)
        record_df["owner_org"] = data_dict['owner_org']
        record_df["private"] = True
        record_df["allow_harvest"] = False
        record_df['tag_string'] = record_df.tag_string.astype(str)
        record_df['tag_string'] = record_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        record_df["created_date"] = pd.to_datetime((pd.to_numeric(record_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+record_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        record_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(record_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+record_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = ['ยุทธศาสตร์ชาติ', 'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', 'แผนความมั่นคงแห่งชาติ','แผนแม่บทภายใต้ยุทธศาสตร์ชาติ','แผนปฏิรูปประเทศ','แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)','นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี','มติคณะรัฐมนตรี','เพื่อการให้บริการประชาชน','กฎหมายที่เกี่ยวข้อง','พันธกิจหน่วยงาน','ดัชนี/ตัวชี้วัดระดับนานาชาติ','ไม่ทราบ']
        record_df['objective_other'] = record_df['objective'].isin(objective_choices)
        record_df['objective_other'] = record_df.objective_other.astype(str)
        record_df['objective_other'] = np.where(record_df['objective_other'] == 'True', 'True', record_df['objective'])
        record_df['objective'] = np.where(record_df['objective_other'] == 'True', record_df['objective'], 'อื่นๆ')
        record_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = ['ไม่ทราบ', 'ปี', 'ครึ่งปี','ไตรมาส','เดือน','สัปดาห์','วัน','วันทำการ','ชั่วโมง','นาที','ตามเวลาจริง','ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        record_df['update_frequency_unit_other'] = record_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        record_df['update_frequency_unit_other'] = record_df.update_frequency_unit_other.astype(str)
        record_df['update_frequency_unit_other'] = np.where(record_df['update_frequency_unit_other'] == 'True', 'True', record_df['update_frequency_unit'])
        record_df['update_frequency_unit'] = np.where(record_df['update_frequency_unit_other'] == 'True', record_df['update_frequency_unit'], 'อื่นๆ')
        record_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = ['ไม่มี', 'โลก', 'ทวีป/กลุ่มประเทศในทวีป','กลุ่มประเทศทางเศรษฐกิจ','ประเทศ','ภาค','จังหวัด','อำเภอ','ตำบล','หมู่บ้าน','เทศบาล/อบต.','พิกัด','ไม่ทราบ']
        record_df['geo_coverage_other'] = record_df['geo_coverage'].isin(geo_coverage_choices)
        record_df['geo_coverage_other'] = record_df.geo_coverage_other.astype(str)
        record_df['geo_coverage_other'] = np.where(record_df['geo_coverage_other'] == 'True', 'True', record_df['geo_coverage'])
        record_df['geo_coverage'] = np.where(record_df['geo_coverage_other'] == 'True', record_df['geo_coverage'], 'อื่นๆ')
        record_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = ['ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        record_df['data_format_other'] = record_df['data_format'].isin(data_format_choices)
        record_df['data_format_other'] = record_df.data_format_other.astype(str)
        record_df['data_format_other'] = np.where(record_df['data_format_other'] == 'True', 'True', record_df['data_format'])
        record_df['data_format'] = np.where(record_df['data_format_other'] == 'True', record_df['data_format'], 'อื่นๆ')
        record_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['License not specified', 'Creative Commons Attributions','Creative Commons Attribution Share-Alike','Creative Commons Non-Commercial (Any)','Open Data Common','GNU Free Documentation License']
        record_df['license_id_other'] = record_df['license_id'].isin(license_id_choices)
        record_df['license_id_other'] = record_df.license_id_other.astype(str)
        record_df['license_id_other'] = np.where(record_df['license_id_other'] == 'True', 'True', record_df['license_id'])
        record_df['license_id'] = np.where(record_df['license_id_other'] == 'True', record_df['license_id'], 'อื่นๆ')
        record_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['','ไม่มี', 'หน่วยงานของรัฐ', 'หน่วยงานเอกชน','หน่วยงาน/องค์กรระหว่างประเทศ','มูลนิธิ/สมาคม','สถาบันการศึกษา']
        record_df['data_support_other'] = record_df['data_support'].isin(data_support_choices)
        record_df['data_support_other'] = record_df.data_support_other.astype(str)
        record_df['data_support_other'] = np.where(record_df['data_support_other'] == 'True', 'True', record_df['data_support'])
        record_df['data_support'] = np.where(record_df['data_support_other'] == 'True', record_df['data_support'], 'อื่นๆ')
        record_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['','ไม่มี','บุคคล', 'ครัวเรือน/ครอบครัว', 'บ้าน/ที่อยู่อาศัย','บริษัท/ห้างร้าน/สถานประกอบการ','อาคาร/สิ่งปลูกสร้าง','พื้นที่การเกษตร ประมง ป่าไม้','สัตว์และพันธุ์พืช','ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่','แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ','เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ','ไม่ทราบ']
        record_df['data_collect_other'] = record_df['data_collect'].isin(data_collect_choices)
        record_df['data_collect_other'] = record_df.data_collect_other.astype(str)
        record_df['data_collect_other'] = np.where(record_df['data_collect_other'] == 'True', 'True', record_df['data_collect'])
        record_df['data_collect'] = np.where(record_df['data_collect_other'] == 'True', record_df['data_collect'], 'อื่นๆ')
        record_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['','ไทย', 'อังกฤษ', 'จีน','มลายู','พม่า','ลาว','เขมร','ญี่ปุ่น','เกาหลี','ฝรั่งเศส','เยอรมัน','อารบิก','ไม่ทราบ']
        record_df['data_language_other'] = record_df['data_language'].isin(data_language_choices)
        record_df['data_language_other'] = record_df.data_language_other.astype(str)
        record_df['data_language_other'] = np.where(record_df['data_language_other'] == 'True', 'True', record_df['data_language'])
        record_df['data_language'] = np.where(record_df['data_language_other'] == 'True', record_df['data_language'], 'อื่นๆ')
        record_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        record_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        record_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        record_df = record_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        record_df.replace(np.nan, '', regex=True, inplace=True)
        
    portal = LocalCKAN()

    package_dict_list = record_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            record_df.loc[record_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            record_df.loc[record_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err).encode('utf-8').decode('unicode-escape')+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Record', dtype=str)
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)

    try:
        final_df = pd.merge(record_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _stat_type_process(data_dict):
    try:
        stat_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Stat', dtype=str)
        stat_df.drop(0, inplace=True)
        stat_df["data_type"] = 'ข้อมูลสถิติ'

        stat_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','first_year_of_data','last_year_of_data','data_release_calendar','last_updated_date','disaggregate','unit_of_measure','unit_of_multiplier','calculation_method','standard','url','data_language','official_statistics','data_type']
        stat_df.drop(['d_type'], axis=1, inplace=True)
        stat_df = stat_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        stat_df.replace(np.nan, '', regex=True, inplace=True)

        stat_df['official_statistics'] = np.where(stat_df['official_statistics'].str.contains("ไม่"), False, True)
        
        stat_df["dataset_name"] = stat_df["name"]
        stat_df["name"] = stat_df["name"].str.lower()
        stat_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            stat_df = stat_df.loc[stat_df['owner_org'] == data_dict['template_org']]
            stat_df.reset_index(drop=True, inplace=True)
        stat_df["owner_org"] = data_dict['owner_org']
        stat_df["private"] = True
        stat_df["allow_harvest"] = False
        stat_df['tag_string'] = stat_df.tag_string.astype(str)
        stat_df['tag_string'] = stat_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        stat_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(stat_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+stat_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = ['ยุทธศาสตร์ชาติ', 'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', 'แผนความมั่นคงแห่งชาติ','แผนแม่บทภายใต้ยุทธศาสตร์ชาติ','แผนปฏิรูปประเทศ','แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)','นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี','มติคณะรัฐมนตรี','เพื่อการให้บริการประชาชน','กฎหมายที่เกี่ยวข้อง','พันธกิจหน่วยงาน','ดัชนี/ตัวชี้วัดระดับนานาชาติ','ไม่ทราบ']
        stat_df['objective_other'] = stat_df['objective'].isin(objective_choices)
        stat_df['objective_other'] = stat_df.objective_other.astype(str)
        stat_df['objective_other'] = np.where(stat_df['objective_other'] == 'True', 'True', stat_df['objective'])
        stat_df['objective'] = np.where(stat_df['objective_other'] == 'True', stat_df['objective'], 'อื่นๆ')
        stat_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = ['ไม่ทราบ', 'ปี', 'ครึ่งปี','ไตรมาส','เดือน','สัปดาห์','วัน','วันทำการ','ชั่วโมง','นาที','ตามเวลาจริง','ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        stat_df['update_frequency_unit_other'] = stat_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        stat_df['update_frequency_unit_other'] = stat_df.update_frequency_unit_other.astype(str)
        stat_df['update_frequency_unit_other'] = np.where(stat_df['update_frequency_unit_other'] == 'True', 'True', stat_df['update_frequency_unit'])
        stat_df['update_frequency_unit'] = np.where(stat_df['update_frequency_unit_other'] == 'True', stat_df['update_frequency_unit'], 'อื่นๆ')
        stat_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = ['ไม่มี', 'โลก', 'ทวีป/กลุ่มประเทศในทวีป','กลุ่มประเทศทางเศรษฐกิจ','ประเทศ','ภาค','จังหวัด','อำเภอ','ตำบล','หมู่บ้าน','เทศบาล/อบต.','พิกัด','ไม่ทราบ']
        stat_df['geo_coverage_other'] = stat_df['geo_coverage'].isin(geo_coverage_choices)
        stat_df['geo_coverage_other'] = stat_df.geo_coverage_other.astype(str)
        stat_df['geo_coverage_other'] = np.where(stat_df['geo_coverage_other'] == 'True', 'True', stat_df['geo_coverage'])
        stat_df['geo_coverage'] = np.where(stat_df['geo_coverage_other'] == 'True', stat_df['geo_coverage'], 'อื่นๆ')
        stat_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = ['ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        stat_df['data_format_other'] = stat_df['data_format'].isin(data_format_choices)
        stat_df['data_format_other'] = stat_df.data_format_other.astype(str)
        stat_df['data_format_other'] = np.where(stat_df['data_format_other'] == 'True', 'True', stat_df['data_format'])
        stat_df['data_format'] = np.where(stat_df['data_format_other'] == 'True', stat_df['data_format'], 'อื่นๆ')
        stat_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['License not specified', 'Creative Commons Attributions','Creative Commons Attribution Share-Alike','Creative Commons Non-Commercial (Any)','Open Data Common','GNU Free Documentation License']
        stat_df['license_id_other'] = stat_df['license_id'].isin(license_id_choices)
        stat_df['license_id_other'] = stat_df.license_id_other.astype(str)
        stat_df['license_id_other'] = np.where(stat_df['license_id_other'] == 'True', 'True', stat_df['license_id'])
        stat_df['license_id'] = np.where(stat_df['license_id_other'] == 'True', stat_df['license_id'], 'อื่นๆ')
        stat_df['license_id_other'].replace('True', '', regex=True, inplace=True)

        stat_df["data_release_calendar"] = pd.to_datetime((pd.to_numeric(stat_df["data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+stat_df["data_release_calendar"].str.slice(start=4), errors='coerce').astype(str)
        
        disaggregate_choices = ['','ไม่มี', 'เพศ', 'อายุ/กลุ่มอายุ','สถานภาพสมรส','ศาสนา','ระดับการศึกษา','อาชีพ','สถานภาพการทำงาน','อุตสาหกรรม/ประเภทกิจการ','รายได้','ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่','ผลิตภัณฑ์','ไม่ทราบ']
        stat_df['disaggregate_other'] = stat_df['disaggregate'].isin(disaggregate_choices)
        stat_df['disaggregate_other'] = stat_df.disaggregate_other.astype(str)
        stat_df['disaggregate_other'] = np.where(stat_df['disaggregate_other'] == 'True', 'True', stat_df['disaggregate'])
        stat_df['disaggregate'] = np.where(stat_df['disaggregate_other'] == 'True', stat_df['disaggregate'], 'อื่นๆ')
        stat_df['disaggregate_other'].replace('True', '', regex=True, inplace=True)
        
        unit_of_multiplier_choices = ['','หน่วย', 'สิบ', 'ร้อย','พัน','หมื่น','แสน','ล้าน','สิบล้าน','ร้อยล้าน','พันล้าน','หมื่นล้าน','แสนล้าน','ล้านล้าน','ไม่ทราบ']
        stat_df['unit_of_multiplier_other'] = stat_df['unit_of_multiplier'].isin(unit_of_multiplier_choices)
        stat_df['unit_of_multiplier_other'] = stat_df.unit_of_multiplier_other.astype(str)
        stat_df['unit_of_multiplier_other'] = np.where(stat_df['unit_of_multiplier_other'] == 'True', 'True', stat_df['unit_of_multiplier'])
        stat_df['unit_of_multiplier'] = np.where(stat_df['unit_of_multiplier_other'] == 'True', stat_df['unit_of_multiplier'], 'อื่นๆ')
        stat_df['unit_of_multiplier_other'].replace('True', '', regex=True, inplace=True)
        
        data_language_choices = ['','ไทย', 'อังกฤษ', 'จีน','มลายู','พม่า','ลาว','เขมร','ญี่ปุ่น','เกาหลี','ฝรั่งเศส','เยอรมัน','อารบิก','ไม่ทราบ']
        stat_df['data_language_other'] = stat_df['data_language'].isin(data_language_choices)
        stat_df['data_language_other'] = stat_df.data_language_other.astype(str)
        stat_df['data_language_other'] = np.where(stat_df['data_language_other'] == 'True', 'True', stat_df['data_language'])
        stat_df['data_language'] = np.where(stat_df['data_language_other'] == 'True', stat_df['data_language'], 'อื่นๆ')
        stat_df['data_language_other'].replace('True', '', regex=True, inplace=True)
        
        stat_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        stat_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','first_year_of_data','last_year_of_data','data_release_calendar','last_updated_date','disaggregate','unit_of_measure','unit_of_multiplier','calculation_method','standard','url','data_language','official_statistics','data_type'])
        stat_df = stat_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        stat_df.replace(np.nan, '', regex=True, inplace=True)

    portal = LocalCKAN()

    package_dict_list = stat_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['disaggregate'] == '':
                pkg_meta.pop('disaggregate', None)
                pkg_meta.pop('disaggregate_other', None)
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            stat_df.loc[stat_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            stat_df.loc[stat_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err).encode('utf-8').decode('unicode-escape')+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Stat', dtype=str)
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics'])
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)

    try:
        final_df = pd.merge(stat_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']

        disaggregate_choices = ['','ไม่มี', 'เพศ', 'อายุ/กลุ่มอายุ','สถานภาพสมรส','ศาสนา','ระดับการศึกษา','อาชีพ','สถานภาพการทำงาน','อุตสาหกรรม/ประเภทกิจการ','รายได้','ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่','ผลิตภัณฑ์','ไม่ทราบ']
        resource_df['resource_disaggregate_other'] = resource_df['resource_disaggregate'].isin(disaggregate_choices)
        resource_df['resource_disaggregate_other'] = resource_df.resource_disaggregate_other.astype(str)
        resource_df['resource_disaggregate_other'] = np.where(resource_df['resource_disaggregate_other'] == 'True', 'True', resource_df['resource_disaggregate'])
        resource_df['resource_disaggregate'] = np.where(resource_df['resource_disaggregate_other'] == 'True', resource_df['resource_disaggregate'], u'อื่นๆ')
        resource_df['resource_disaggregate_other'].replace('True', '', regex=True, inplace=True)

        resource_df["resource_data_release_calendar"] = pd.to_datetime((pd.to_numeric(resource_df["resource_data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_data_release_calendar"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            if res_meta['resource_disaggregate'] == '':
                res_meta.pop('resource_disaggregate', None)
                res_meta.pop('resource_disaggregate_other', None)
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _gis_type_process(data_dict):
    try:
        gis_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_GIS', dtype=str)
        gis_df.drop(0, inplace=True)
        gis_df["data_type"] = 'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'

        gis_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','geographic_data_set','equivalent_scale','west_bound_longitude','east_bound_longitude','north_bound_longitude','south_bound_longitude','positional_accuracy','reference_period','last_updated_date','data_release_calendar','data_release_date','url','data_language','data_type']
        gis_df.drop(['d_type'], axis=1, inplace=True)
        gis_df = gis_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        gis_df.replace(np.nan, '', regex=True, inplace=True)

        gis_df["dataset_name"] = gis_df["name"]
        gis_df["name"] = gis_df["name"].str.lower()
        gis_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            gis_df = gis_df.loc[gis_df['owner_org'] == data_dict['template_org']]
            gis_df.reset_index(drop=True, inplace=True)
        gis_df["owner_org"] = data_dict['owner_org']
        gis_df["private"] = True
        gis_df["allow_harvest"] = False
        gis_df['tag_string'] = gis_df.tag_string.astype(str)
        gis_df['tag_string'] = gis_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        gis_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(gis_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = ['ยุทธศาสตร์ชาติ', 'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', 'แผนความมั่นคงแห่งชาติ','แผนแม่บทภายใต้ยุทธศาสตร์ชาติ','แผนปฏิรูปประเทศ','แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)','นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี','มติคณะรัฐมนตรี','เพื่อการให้บริการประชาชน','กฎหมายที่เกี่ยวข้อง','พันธกิจหน่วยงาน','ดัชนี/ตัวชี้วัดระดับนานาชาติ','ไม่ทราบ']
        gis_df['objective_other'] = gis_df['objective'].isin(objective_choices)
        gis_df['objective_other'] = gis_df.objective_other.astype(str)
        gis_df['objective_other'] = np.where(gis_df['objective_other'] == 'True', 'True', gis_df['objective'])
        gis_df['objective'] = np.where(gis_df['objective_other'] == 'True', gis_df['objective'], 'อื่นๆ')
        gis_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = ['ไม่ทราบ', 'ปี', 'ครึ่งปี','ไตรมาส','เดือน','สัปดาห์','วัน','วันทำการ','ชั่วโมง','นาที','ตามเวลาจริง','ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        gis_df['update_frequency_unit_other'] = gis_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        gis_df['update_frequency_unit_other'] = gis_df.update_frequency_unit_other.astype(str)
        gis_df['update_frequency_unit_other'] = np.where(gis_df['update_frequency_unit_other'] == 'True', 'True', gis_df['update_frequency_unit'])
        gis_df['update_frequency_unit'] = np.where(gis_df['update_frequency_unit_other'] == 'True', gis_df['update_frequency_unit'], 'อื่นๆ')
        gis_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = ['ไม่มี', 'โลก', 'ทวีป/กลุ่มประเทศในทวีป','กลุ่มประเทศทางเศรษฐกิจ','ประเทศ','ภาค','จังหวัด','อำเภอ','ตำบล','หมู่บ้าน','เทศบาล/อบต.','พิกัด','ไม่ทราบ']
        gis_df['geo_coverage_other'] = gis_df['geo_coverage'].isin(geo_coverage_choices)
        gis_df['geo_coverage_other'] = gis_df.geo_coverage_other.astype(str)
        gis_df['geo_coverage_other'] = np.where(gis_df['geo_coverage_other'] == 'True', 'True', gis_df['geo_coverage'])
        gis_df['geo_coverage'] = np.where(gis_df['geo_coverage_other'] == 'True', gis_df['geo_coverage'], 'อื่นๆ')
        gis_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = ['ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        gis_df['data_format_other'] = gis_df['data_format'].isin(data_format_choices)
        gis_df['data_format_other'] = gis_df.data_format_other.astype(str)
        gis_df['data_format_other'] = np.where(gis_df['data_format_other'] == 'True', 'True', gis_df['data_format'])
        gis_df['data_format'] = np.where(gis_df['data_format_other'] == 'True', gis_df['data_format'], 'อื่นๆ')
        gis_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['License not specified', 'Creative Commons Attributions','Creative Commons Attribution Share-Alike','Creative Commons Non-Commercial (Any)','Open Data Common','GNU Free Documentation License']
        gis_df['license_id_other'] = gis_df['license_id'].isin(license_id_choices)
        gis_df['license_id_other'] = gis_df.license_id_other.astype(str)
        gis_df['license_id_other'] = np.where(gis_df['license_id_other'] == 'True', 'True', gis_df['license_id'])
        gis_df['license_id'] = np.where(gis_df['license_id_other'] == 'True', gis_df['license_id'], 'อื่นๆ')
        gis_df['license_id_other'].replace('True', '', regex=True, inplace=True)

        equivalent_scale_choices = ['','1:4,000', '1:10,000', '1:25,000','1:50,000','1:250,000']
        gis_df['equivalent_scale_other'] = gis_df['equivalent_scale'].isin(equivalent_scale_choices)
        gis_df['equivalent_scale_other'] = gis_df.equivalent_scale_other.astype(str)
        gis_df['equivalent_scale_other'] = np.where(gis_df['equivalent_scale_other'] == 'True', 'True', gis_df['equivalent_scale'])
        gis_df['equivalent_scale'] = np.where(gis_df['equivalent_scale_other'] == 'True', gis_df['equivalent_scale'], 'อื่นๆ')
        gis_df['equivalent_scale_other'].replace('True', '', regex=True, inplace=True)

        gis_df["data_release_calendar"] = pd.to_datetime((pd.to_numeric(gis_df["data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["data_release_calendar"].str.slice(start=4),errors='coerce').astype(str)
        gis_df["data_release_date"] = pd.to_datetime((pd.to_numeric(gis_df["data_release_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["data_release_date"].str.slice(start=4),errors='coerce').astype(str)

        data_language_choices = ['','ไทย', 'อังกฤษ', 'จีน','มลายู','พม่า','ลาว','เขมร','ญี่ปุ่น','เกาหลี','ฝรั่งเศส','เยอรมัน','อารบิก','ไม่ทราบ']
        gis_df['data_language_other'] = gis_df['data_language'].isin(data_language_choices)
        gis_df['data_language_other'] = gis_df.data_language_other.astype(str)
        gis_df['data_language_other'] = np.where(gis_df['data_language_other'] == 'True', 'True', gis_df['data_language'])
        gis_df['data_language'] = np.where(gis_df['data_language_other'] == 'True', gis_df['data_language'], 'อื่นๆ')
        gis_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        gis_df.replace('NaT', '', regex=True, inplace=True)

    except Exception as err:
        log.info(err)
        gis_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','geographic_data_set','equivalent_scale','west_bound_longitude','east_bound_longitude','north_bound_longitude','south_bound_longitude','positional_accuracy','reference_period','last_updated_date','data_release_calendar','data_release_date','url','data_language','data_type'])
        gis_df = gis_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        gis_df.replace(np.nan, '', regex=True, inplace=True)

    portal = LocalCKAN()

    package_dict_list = gis_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            gis_df.loc[gis_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            gis_df.loc[gis_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err).encode('utf-8').decode('unicode-escape')+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_GIS', dtype=str)
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy'])
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)

    try:
        final_df = pd.merge(gis_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_data_release_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_data_release_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_data_release_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _multi_type_process(data_dict):
    try:
        multi_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Multi', dtype=str)
        multi_df.drop(0, inplace=True)
        multi_df["data_type"] = 'ข้อมูลหลากหลายประเภท'

        multi_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        multi_df.drop(['d_type'], axis=1, inplace=True)
        multi_df = multi_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        multi_df.replace(np.nan, '', regex=True, inplace=True)

        multi_df['high_value_dataset'] = np.where(multi_df['high_value_dataset'].str.contains("ไม่"), False, True)
        multi_df['reference_data'] = np.where(multi_df['reference_data'].str.contains("ไม่"), False, True)
        
        multi_df["dataset_name"] = multi_df["name"]
        multi_df["name"] = multi_df["name"].str.lower()
        multi_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            multi_df = multi_df.loc[multi_df['owner_org'] == data_dict['template_org']]
            multi_df.reset_index(drop=True, inplace=True)
        multi_df["owner_org"] = data_dict['owner_org']
        multi_df["private"] = True
        multi_df["allow_harvest"] = False
        multi_df['tag_string'] = multi_df.tag_string.astype(str)
        multi_df['tag_string'] = multi_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        multi_df["created_date"] = pd.to_datetime((pd.to_numeric(multi_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+multi_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        multi_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(multi_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+multi_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = ['ยุทธศาสตร์ชาติ', 'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', 'แผนความมั่นคงแห่งชาติ','แผนแม่บทภายใต้ยุทธศาสตร์ชาติ','แผนปฏิรูปประเทศ','แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)','นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี','มติคณะรัฐมนตรี','เพื่อการให้บริการประชาชน','กฎหมายที่เกี่ยวข้อง','พันธกิจหน่วยงาน','ดัชนี/ตัวชี้วัดระดับนานาชาติ','ไม่ทราบ']
        multi_df['objective_other'] = multi_df['objective'].isin(objective_choices)
        multi_df['objective_other'] = multi_df.objective_other.astype(str)
        multi_df['objective_other'] = np.where(multi_df['objective_other'] == 'True', 'True', multi_df['objective'])
        multi_df['objective'] = np.where(multi_df['objective_other'] == 'True', multi_df['objective'], 'อื่นๆ')
        multi_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = ['ไม่ทราบ', 'ปี', 'ครึ่งปี','ไตรมาส','เดือน','สัปดาห์','วัน','วันทำการ','ชั่วโมง','นาที','ตามเวลาจริง','ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        multi_df['update_frequency_unit_other'] = multi_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        multi_df['update_frequency_unit_other'] = multi_df.update_frequency_unit_other.astype(str)
        multi_df['update_frequency_unit_other'] = np.where(multi_df['update_frequency_unit_other'] == 'True', 'True', multi_df['update_frequency_unit'])
        multi_df['update_frequency_unit'] = np.where(multi_df['update_frequency_unit_other'] == 'True', multi_df['update_frequency_unit'], 'อื่นๆ')
        multi_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = ['ไม่มี', 'โลก', 'ทวีป/กลุ่มประเทศในทวีป','กลุ่มประเทศทางเศรษฐกิจ','ประเทศ','ภาค','จังหวัด','อำเภอ','ตำบล','หมู่บ้าน','เทศบาล/อบต.','พิกัด','ไม่ทราบ']
        multi_df['geo_coverage_other'] = multi_df['geo_coverage'].isin(geo_coverage_choices)
        multi_df['geo_coverage_other'] = multi_df.geo_coverage_other.astype(str)
        multi_df['geo_coverage_other'] = np.where(multi_df['geo_coverage_other'] == 'True', 'True', multi_df['geo_coverage'])
        multi_df['geo_coverage'] = np.where(multi_df['geo_coverage_other'] == 'True', multi_df['geo_coverage'], 'อื่นๆ')
        multi_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = ['ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        multi_df['data_format_other'] = multi_df['data_format'].isin(data_format_choices)
        multi_df['data_format_other'] = multi_df.data_format_other.astype(str)
        multi_df['data_format_other'] = np.where(multi_df['data_format_other'] == 'True', 'True', multi_df['data_format'])
        multi_df['data_format'] = np.where(multi_df['data_format_other'] == 'True', multi_df['data_format'], 'อื่นๆ')
        multi_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['License not specified', 'Creative Commons Attributions','Creative Commons Attribution Share-Alike','Creative Commons Non-Commercial (Any)','Open Data Common','GNU Free Documentation License']
        multi_df['license_id_other'] = multi_df['license_id'].isin(license_id_choices)
        multi_df['license_id_other'] = multi_df.license_id_other.astype(str)
        multi_df['license_id_other'] = np.where(multi_df['license_id_other'] == 'True', 'True', multi_df['license_id'])
        multi_df['license_id'] = np.where(multi_df['license_id_other'] == 'True', multi_df['license_id'], 'อื่นๆ')
        multi_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['','ไม่มี', 'หน่วยงานของรัฐ', 'หน่วยงานเอกชน','หน่วยงาน/องค์กรระหว่างประเทศ','มูลนิธิ/สมาคม','สถาบันการศึกษา']
        multi_df['data_support_other'] = multi_df['data_support'].isin(data_support_choices)
        multi_df['data_support_other'] = multi_df.data_support_other.astype(str)
        multi_df['data_support_other'] = np.where(multi_df['data_support_other'] == 'True', 'True', multi_df['data_support'])
        multi_df['data_support'] = np.where(multi_df['data_support_other'] == 'True', multi_df['data_support'], 'อื่นๆ')
        multi_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['','ไม่มี','บุคคล', 'ครัวเรือน/ครอบครัว', 'บ้าน/ที่อยู่อาศัย','บริษัท/ห้างร้าน/สถานประกอบการ','อาคาร/สิ่งปลูกสร้าง','พื้นที่การเกษตร ประมง ป่าไม้','สัตว์และพันธุ์พืช','ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่','แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ','เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ','ไม่ทราบ']
        multi_df['data_collect_other'] = multi_df['data_collect'].isin(data_collect_choices)
        multi_df['data_collect_other'] = multi_df.data_collect_other.astype(str)
        multi_df['data_collect_other'] = np.where(multi_df['data_collect_other'] == 'True', 'True', multi_df['data_collect'])
        multi_df['data_collect'] = np.where(multi_df['data_collect_other'] == 'True', multi_df['data_collect'], 'อื่นๆ')
        multi_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['','ไทย', 'อังกฤษ', 'จีน','มลายู','พม่า','ลาว','เขมร','ญี่ปุ่น','เกาหลี','ฝรั่งเศส','เยอรมัน','อารบิก','ไม่ทราบ']
        multi_df['data_language_other'] = multi_df['data_language'].isin(data_language_choices)
        multi_df['data_language_other'] = multi_df.data_language_other.astype(str)
        multi_df['data_language_other'] = np.where(multi_df['data_language_other'] == 'True', 'True', multi_df['data_language'])
        multi_df['data_language'] = np.where(multi_df['data_language_other'] == 'True', multi_df['data_language'], 'อื่นๆ')
        multi_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        multi_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        multi_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        multi_df = multi_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        multi_df.replace(np.nan, '', regex=True, inplace=True)
        
    portal = LocalCKAN()

    package_dict_list = multi_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            multi_df.loc[multi_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            multi_df.loc[multi_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err).encode('utf-8').decode('unicode-escape')+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Multi', dtype=str)
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)

    try:
        final_df = pd.merge(multi_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _other_type_process(data_dict):
    try:
        other_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Other', dtype=str)
        other_df.drop(0, inplace=True)
        other_df["data_type"] = 'ข้อมูลประเภทอื่นๆ'

        other_df.columns = ['name','data_type_other','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        other_df = other_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        other_df.replace(np.nan, '', regex=True, inplace=True)

        other_df['high_value_dataset'] = np.where(other_df['high_value_dataset'].str.contains("ไม่"), False, True)
        other_df['reference_data'] = np.where(other_df['reference_data'].str.contains("ไม่"), False, True)
        
        other_df["dataset_name"] = other_df["name"]
        other_df["name"] = other_df["name"].str.lower()
        other_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            other_df = other_df.loc[other_df['owner_org'] == data_dict['template_org']]
            other_df.reset_index(drop=True, inplace=True)
        other_df["owner_org"] = data_dict['owner_org']
        other_df["private"] = True
        other_df["allow_harvest"] = False
        other_df['tag_string'] = other_df.tag_string.astype(str)
        other_df['tag_string'] = other_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        other_df["created_date"] = pd.to_datetime((pd.to_numeric(other_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+other_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        other_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(other_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+other_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = ['ยุทธศาสตร์ชาติ', 'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', 'แผนความมั่นคงแห่งชาติ','แผนแม่บทภายใต้ยุทธศาสตร์ชาติ','แผนปฏิรูปประเทศ','แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)','นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี','มติคณะรัฐมนตรี','เพื่อการให้บริการประชาชน','กฎหมายที่เกี่ยวข้อง','พันธกิจหน่วยงาน','ดัชนี/ตัวชี้วัดระดับนานาชาติ','ไม่ทราบ']
        other_df['objective_other'] = other_df['objective'].isin(objective_choices)
        other_df['objective_other'] = other_df.objective_other.astype(str)
        other_df['objective_other'] = np.where(other_df['objective_other'] == 'True', 'True', other_df['objective'])
        other_df['objective'] = np.where(other_df['objective_other'] == 'True', other_df['objective'], 'อื่นๆ')
        other_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = ['ไม่ทราบ', 'ปี', 'ครึ่งปี','ไตรมาส','เดือน','สัปดาห์','วัน','วันทำการ','ชั่วโมง','นาที','ตามเวลาจริง','ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        other_df['update_frequency_unit_other'] = other_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        other_df['update_frequency_unit_other'] = other_df.update_frequency_unit_other.astype(str)
        other_df['update_frequency_unit_other'] = np.where(other_df['update_frequency_unit_other'] == 'True', 'True', other_df['update_frequency_unit'])
        other_df['update_frequency_unit'] = np.where(other_df['update_frequency_unit_other'] == 'True', other_df['update_frequency_unit'], 'อื่นๆ')
        other_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = ['ไม่มี', 'โลก', 'ทวีป/กลุ่มประเทศในทวีป','กลุ่มประเทศทางเศรษฐกิจ','ประเทศ','ภาค','จังหวัด','อำเภอ','ตำบล','หมู่บ้าน','เทศบาล/อบต.','พิกัด','ไม่ทราบ']
        other_df['geo_coverage_other'] = other_df['geo_coverage'].isin(geo_coverage_choices)
        other_df['geo_coverage_other'] = other_df.geo_coverage_other.astype(str)
        other_df['geo_coverage_other'] = np.where(other_df['geo_coverage_other'] == 'True', 'True', other_df['geo_coverage'])
        other_df['geo_coverage'] = np.where(other_df['geo_coverage_other'] == 'True', other_df['geo_coverage'], 'อื่นๆ')
        other_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = ['ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        other_df['data_format_other'] = other_df['data_format'].isin(data_format_choices)
        other_df['data_format_other'] = other_df.data_format_other.astype(str)
        other_df['data_format_other'] = np.where(other_df['data_format_other'] == 'True', 'True', other_df['data_format'])
        other_df['data_format'] = np.where(other_df['data_format_other'] == 'True', other_df['data_format'], 'อื่นๆ')
        other_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['License not specified', 'Creative Commons Attributions','Creative Commons Attribution Share-Alike','Creative Commons Non-Commercial (Any)','Open Data Common','GNU Free Documentation License']
        other_df['license_id_other'] = other_df['license_id'].isin(license_id_choices)
        other_df['license_id_other'] = other_df.license_id_other.astype(str)
        other_df['license_id_other'] = np.where(other_df['license_id_other'] == 'True', 'True', other_df['license_id'])
        other_df['license_id'] = np.where(other_df['license_id_other'] == 'True', other_df['license_id'], 'อื่นๆ')
        other_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['','ไม่มี', 'หน่วยงานของรัฐ', 'หน่วยงานเอกชน','หน่วยงาน/องค์กรระหว่างประเทศ','มูลนิธิ/สมาคม','สถาบันการศึกษา']
        other_df['data_support_other'] = other_df['data_support'].isin(data_support_choices)
        other_df['data_support_other'] = other_df.data_support_other.astype(str)
        other_df['data_support_other'] = np.where(other_df['data_support_other'] == 'True', 'True', other_df['data_support'])
        other_df['data_support'] = np.where(other_df['data_support_other'] == 'True', other_df['data_support'], 'อื่นๆ')
        other_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['','ไม่มี','บุคคล', 'ครัวเรือน/ครอบครัว', 'บ้าน/ที่อยู่อาศัย','บริษัท/ห้างร้าน/สถานประกอบการ','อาคาร/สิ่งปลูกสร้าง','พื้นที่การเกษตร ประมง ป่าไม้','สัตว์และพันธุ์พืช','ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่','แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ','เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ','ไม่ทราบ']
        other_df['data_collect_other'] = other_df['data_collect'].isin(data_collect_choices)
        other_df['data_collect_other'] = other_df.data_collect_other.astype(str)
        other_df['data_collect_other'] = np.where(other_df['data_collect_other'] == 'True', 'True', other_df['data_collect'])
        other_df['data_collect'] = np.where(other_df['data_collect_other'] == 'True', other_df['data_collect'], 'อื่นๆ')
        other_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['','ไทย', 'อังกฤษ', 'จีน','มลายู','พม่า','ลาว','เขมร','ญี่ปุ่น','เกาหลี','ฝรั่งเศส','เยอรมัน','อารบิก','ไม่ทราบ']
        other_df['data_language_other'] = other_df['data_language'].isin(data_language_choices)
        other_df['data_language_other'] = other_df.data_language_other.astype(str)
        other_df['data_language_other'] = np.where(other_df['data_language_other'] == 'True', 'True', other_df['data_language'])
        other_df['data_language'] = np.where(other_df['data_language_other'] == 'True', other_df['data_language'], 'อื่นๆ')
        other_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        other_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        other_df = pd.DataFrame(columns=['name','data_type_other','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        other_df = other_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        other_df.replace(np.nan, '', regex=True, inplace=True)

    portal = LocalCKAN()

    package_dict_list = other_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            other_df.loc[other_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            other_df.loc[other_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err).encode('utf-8').decode('unicode-escape')+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Other', dtype=str)
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        resource_df.replace(np.nan, '', regex=True, inplace=True)

    try:
        final_df = pd.merge(other_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _finished_process(data_dict):
    portal = LocalCKAN()
    log_str = 'import finished: '+datetime.datetime.now().isoformat()+' -- จบการทำงาน\n'
    activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Finished", "import_log": log_str}, 
        "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
        "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
        "activity_type": "changed user"
        }
    portal.action.activity_create(**activity_dict)
    log.info(log_str)