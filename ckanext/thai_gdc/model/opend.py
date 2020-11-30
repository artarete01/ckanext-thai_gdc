# -*- coding: utf-8 -*-
import ckan.model as model
import ckan.plugins.toolkit as toolkit

class OpendModel:

    def get_all_view(self):
        sql = '''
            select sum(count) as page_view from tracking_summary where tracking_type = 'page'
        '''
        resultproxy = model.Session.execute(sql)
        row = resultproxy.fetchone()
        return row['page_view'] is not None and row['page_view'] or 0

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