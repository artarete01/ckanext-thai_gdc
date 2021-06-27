# -*- coding: utf-8 -*-
import ckan.model as model
import ckan.plugins.toolkit as toolkit
from sqlalchemy.exc import SQLAlchemyError
import logging

log = logging.getLogger(__name__)

class OpendModel:
    def get_dataset_bulk_import_log(self, import_id):
        sql = "select split_part(split_part(\"data\",'\"import_log\": \"',2),'\\n\"}',1) as log_content from activity a where \"data\" like '%\"import_id\": \""+import_id+"\", \"import_status\": \"Running\"%'"

        resultproxy = model.Session.execute(sql)

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data

    def get_users_non_member(self):
        sql = '''
            select u.id from "user" u where u.sysadmin is false and u.state = 'active' and u.id not in  (select distinct m.table_id from "member" m where m.table_name = 'user' and m.state = 'active')
        '''

        resultproxy = model.Session.execute(sql)

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data

    def get_all_view(self):
        sql = '''
            select sum(count) as page_view from tracking_summary where tracking_type = 'page'
        '''
        try:
            resultproxy = model.Session.execute(sql)
            row = resultproxy.fetchone()
            model.Session.commit()
            return row['page_view'] is not None and row['page_view'] or 0
        except SQLAlchemyError as e:
            print(str(e))
            model.Session.rollback()
            return 0

    def get_last_update_tracking(self):
        sql = '''
            select max(tracking_date) as last_tracking from tracking_summary
        '''
        try:
            resultproxy = model.Session.execute(sql)
            row = resultproxy.fetchone()
            model.Session.commit()
            return row['last_tracking'] is not None and row['last_tracking'] or 0
        except SQLAlchemyError as e:
            print(str(e))
            model.Session.rollback()
            return 0

    def get_resource_download_top(self, limit):
        sql = '''
            select row_number() over (order by sum(count) desc, pa.title) as rownum, ts.url,sum(count) as sum, replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') as package_id, 
            replace(replace(substring(ts.url from '\/resource\/.*\/download\/'),'/resource/',''),'/download/','') as resource_id, re."name" as resource_name, pa.title as package_name, 
            (select me.group_id from "member" me where me.table_id = replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') and me.table_name ='package' and me.capacity = 'public' and me.state = 'active' order by me.group_id limit 1) as group_id,
            (select gr.title from "group" gr where gr.id = (select me.group_id from "member" me where me.table_id = replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') and me.table_name ='package' and me.capacity = 'public' and me.state = 'active' order by me.group_id limit 1)) as group_title,
            (select gr.name from "group" gr where gr.id = (select me.group_id from "member" me where me.table_id = replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') and me.table_name ='package' and me.capacity = 'public' and me.state = 'active' order by me.group_id limit 1)) as group_name,
            (select gr.image_url from "group" gr where gr.id = (select me.group_id from "member" me where me.table_id = replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') and me.table_name ='package' and me.capacity = 'public' and me.state = 'active' order by me.group_id limit 1)) as group_image_url
            from tracking_summary ts inner join resource re on re.id = replace(replace(substring(ts.url from '\/resource\/.*\/download\/'),'/resource/',''),'/download/','') 
            inner join package pa on pa.id = replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') 
            where ts.tracking_type ='resource' and ts.url like '%/download/%' and re.state = 'active' and pa.private = false group by ts.url, re.name, pa.title order by sum desc, pa.title limit {} 
        '''.format(limit)

        resultproxy = model.Session.execute(sql)

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data
    
    def get_resource_download(self, resource_id):
        sql = '''
                select ts.url,sum(count) as sum, replace(replace(substring(ts.url from '\/dataset\/.*\/resource\/'),'/dataset/',''),'/resource/','') as package_id, 
            replace(replace(substring(ts.url from '\/resource\/.*\/download\/'),'/resource/',''),'/download/','') as resource_id
            from tracking_summary ts 
            where ts.tracking_type ='resource' and ts.url like '%/download/%' and replace(replace(substring(ts.url from '\/resource\/.*\/download\/'),'/resource/',''),'/download/','') = '{}' group by ts.url
              '''.format(resource_id)
        
        resultproxy = model.Session.execute(sql)
        row = resultproxy.fetchone()
        return 0 if row is None else row['sum']
    
    def get_featured_pages(self, limit):
        if limit > 0:
            sql = '''
                select row_number() over (order by publish_date, modified desc) as rownum, cp.* from ckanext_pages cp where extras like '%"featured": true%' and page_type = 'page' and private = false order by publish_date, modified desc limit {} 
            '''.format(limit)
        else:
            sql = '''
                select row_number() over (order by publish_date, modified desc) as rownum, cp.* from ckanext_pages cp where extras like '%"featured": true%' and page_type = 'page' and private = false order by publish_date, modified desc 
            '''

        resultproxy = model.Session.execute(sql)

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data
    
    def get_page(self, name):
        sql = '''
            select cp.* from ckanext_pages cp where name = '{}' 
        '''.format(name)
        try:
            resultproxy = model.Session.execute(sql)
        except:
            return None

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data
    
    def get_groups_all_type(self, type=None):
        sql = '''
            select gr.id, gr.title as display_name, gr.type from "group" gr where is_organization = false and state = 'active'
        '''
        if type:
            sql = sql + '''
             and "type"='{}'
        '''.format(type)
        
        resultproxy = model.Session.execute(sql)

        data = []
        for rowproxy in resultproxy:
            my_dict = {column: value for column, value in rowproxy.items()}
            data.append(my_dict)

        return data