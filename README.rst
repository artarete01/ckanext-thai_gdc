=============
ckanext-thai_gdc
=============

CKAN Extension เพื่อสนับสนุนการจัดทำ Government Data Catalog (ckanext-thai_gdc) มีวัตถุประสงค์ให้หน่วยงานภาครัฐของไทยนำไปติดตั้งเพื่อสร้าง "ระบบบัญชีข้อมูลหน่วยงาน (Agency Data Catalog)" ตามโครงการศึกษาและพัฒนาต้นแบบระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog) และระบบนามานุกรม (Directory Service) โดยความร่วมมือของสำนักงานสถิติแห่งชาติ (สสช.) สำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) (สพร.) สถาบันส่งเสริมการวิเคราะห์และบริหารข้อมูลขนาดใหญ่ภาครัฐ (สวข.) สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง และศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ 

โดย ckanext-thai_gdc มีคุณสมบัติทางเทคนิค ดังนี้

- รองรับการ Tag และ Search ภาษาไทย
- เมทาดาตา (metadata) เป็นไปตาม `มาตรฐานคำอธิบายข้อมูลหรือเมทาดาตาสำหรับชุดข้อมูลภาครัฐ <https://www.dga.or.th/wp-content/uploads/2021/03/Final_GD-Catalog-Guideline-v.1.0_16032564-3.pdf>`_ ที่กำหนดโดยสำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) ร่วมกับสำนักงานสถิติแห่งชาติ และสถาบันส่งเสริมการวิเคราะห์และบริหารข้อมูลขนาดใหญ่ภาครัฐ
- รองรับการสร้าง Dataset ที่ไม่จำเป็นต้องมี Resource โดยไม่ติดสถานะ draft
- อนุญาตให้ผู้ใช้ที่เป็น editor สามารถกำหนด group ให้กับ dataset ได้
- รองรับการตั้งค่ารายละเอียดเว็บไซต์ที่จำเป็นสำหรับ Sysadmin เช่น banner footer ผ่านหน้า UI
- แสดงสถิติจำนวนผู้เข้าชมสำหรับ Dataset และสถิติการดาวน์โหลดสำหรับ Resource
- รองรับการเชื่อมโยง Catalog (Harvesting) กับระบบบัญชีข้อมูลกลางภาครัฐ (Government Data Catalog)
- รองรับการทำ data visualization ชุดข้อมูลเปิด โดยผ่านแพลตฟอร์ม Open-D
- รองรับการ Import ชุดข้อมูลจากไฟล์ `Template การจัดทำบัญชีข้อมูลในแบบไฟล์ excel <https://gdhelppage.nso.go.th/p00_01_019.html>`_

------------
Requirements
------------

สามารถติดตั้งร่วมกับ CKAN 2.9.1 ขึ้นไป โดยจำเป็นต้องติดตั้ง Extensions เหล่านี้ก่อน 

- `ckanext-scheming <https://gitlab.nectec.or.th/opend/installing-ckan/-/blob/master/ckan-extension.md#2-ckanext-scheming>`_
- `ckanext-hierarchy <https://gitlab.nectec.or.th/opend/installing-ckan/-/blob/master/ckan-extension.md#3-ckanext-hierarchy>`_

------------
การติดตั้ง (Installation)
------------

- `ckanext-thai_gdc <https://gitlab.nectec.or.th/opend/installing-ckan/-/blob/master/ckan-extension.md#5-ckanext-thai_gdc>`_

------------
การปรับปรุง (Update)
------------

ตัวอย่างขั้นตอนการปรับปรุง extension
- `วิธีการ update ckanext-thai_gdc <https://gitlab.nectec.or.th/opend/installing-ckan/-/blob/master/ckan-extension.md#update-ckanext-thai_gdc>`_

------------
ข้อมูลเพิ่มเติม
------------

- `ระบบบัญชีข้อมูลภาครัฐ - Government Data Catalog (GD Catalog) <https://gdhelppage.nso.go.th>`_
- `ปลดล็อค ! ข้อจำกัดการสร้าง Data Catalog ด้วยแพลตฟอร์มจัดการข้อมูลบริบทไทย) <https://www.nectec.or.th/news/news-article/data-catalog-platform.html>`_

