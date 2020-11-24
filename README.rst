=============
ckanext-nectec_opend
=============

CKAN Extension เพื่อให้หน่วยงานภาครัฐของไทยนำไปติดตั้งเพื่อสร้าง "ระบบบัญชีข้อมูลหน่วยงาน (Agency Data Catalog)" ตามโครงการศึกษาและพัฒนาต้นแบบระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog) และระบบนามานุกรม (Directory Service) ด้วยความร่วมมือระหว่างสำนักงานสถิติแห่งชาติ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง และศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ โดยมีคุณสมบัติทางเทคนิค ดังนี้

- รองรับการ Tag และ full text search ภาษาไทย
- Metadata เป็นไปตามมาตรฐานที่กำหนดโดยสำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน)
- รองรับการสร้าง Dataset ที่ไม่จำเป็นต้องมี Resource โดยไม่ติดสถานะ draft
- รองรับการตั้งค่ารายละเอียดเว็บไซต์ที่จำเป็นสำหรับ Sysadmin เช่น banner footer ผ่านหน้า UI
- แสดงสถิติจำนวนผู้เข้าชมสำหรับ Dataset และสถิติการ download สำหรับ Resource
- รองรับการเชื่อมโยง Catalog (Harvesting) กับระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog)

------------
Requirements
------------

สามารถติดตั้งร่วมกับ CKAN 2.8 ขึ้นไป โดยจำเป็นต้องติดตั้ง [ckanext-scheming](https://github.com/ckan/ckanext-scheming) และ [ckanext-pages](https://github.com/ckan/ckanext-pages)


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-nectec_opend:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-nectec_opend Python package into your virtual environment::

     pip install ckanext-nectec_opend

3. Add ``nectec_opend`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

module-path:file to schemas being used

    scheming.dataset_schemas = ckanext.nectec_opend:ckan_dataset.json
