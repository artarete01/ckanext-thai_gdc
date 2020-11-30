=============
ckanext-thai_gdc
=============

CKAN Extension เพื่อให้หน่วยงานภาครัฐของไทยนำไปติดตั้งเพื่อสร้าง "ระบบบัญชีข้อมูลหน่วยงาน (Agency Data Catalog)" ตามโครงการศึกษาและพัฒนาต้นแบบระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog) และระบบนามานุกรม (Directory Service) โดยความร่วมมือของสำนักงานสถิติแห่งชาติ (สสช.) สำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) (สพร.) สถาบันส่งเสริมการวิเคราะห์และบริหารข้อมูลขนาดใหญ่ภาครัฐ (สวข.) สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง และศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ 

โดย extension มีคุณสมบัติทางเทคนิค ดังนี้

- รองรับการ Tag และ Search ภาษาไทย
- เมทาดาตา (metadata) เป็นไปตามมาตรฐานคำอธิบายข้อมูลหรือเมทาดาตาสำหรับชุดข้อมูลภาครัฐ ที่กำหนดโดยสำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) ร่วมกับสำนักงานสถิติแห่งชาติ และสถาบันส่งเสริมการวิเคราะห์และบริหารข้อมูลขนาดใหญ่ภาครัฐ
- รองรับการสร้าง Dataset ที่ไม่จำเป็นต้องมี Resource โดยไม่ติดสถานะ draft
- รองรับการตั้งค่ารายละเอียดเว็บไซต์ที่จำเป็นสำหรับ Sysadmin เช่น banner footer ผ่านหน้า UI
- แสดงสถิติจำนวนผู้เข้าชมสำหรับ Dataset และสถิติการดาวน์โหลดสำหรับ Resource
- รองรับการเชื่อมโยง Catalog (Harvesting) กับระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog)

------------
Requirements
------------

สามารถติดตั้งร่วมกับ CKAN 2.8 ขึ้นไป โดยจำเป็นต้องติดตั้ง Extensions เหล่านี้ก่อน 

- https://github.com/ckan/ckanext-scheming
- https://github.com/ckan/ckanext-pages


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-thai_gdc:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-thai_gdc Python package, from your CKAN virtualenv, run the following from your CKAN base folder (/usr/lib/ckan/default)::

     pip install -e 'git+https://gitlab.nectec.or.th/opend/ckanext-thai_gdc.git#egg=ckanext-thai_gdc'

3. Add ``thai_gdc`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

module-path:file for dataset schema

     scheming.dataset_schemas = ckanext.thai_gdc:ckan_dataset.json
