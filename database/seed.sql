-- ============================================================
-- Seed data for asset_management database.
-- Run AFTER schema.sql:  mysql -u root -p asset_management < database/seed.sql
-- ============================================================
USE asset_management;

-- ------------------------------------------------------------
-- ROLES
-- ------------------------------------------------------------
INSERT INTO roles (name) VALUES ('SUPER_ADMIN'), ('ADMIN'), ('EMPLOYEE');

-- ------------------------------------------------------------
-- PERMISSIONS
-- ------------------------------------------------------------
INSERT INTO permissions (code, label) VALUES
('VIEW_ASSETS','View Assets'),
('ADD_ASSETS','Add Assets'),
('EDIT_ASSETS','Edit Assets'),
('DELETE_ASSETS','Delete Assets'),
('VIEW_EMPLOYEES','View Employees'),
('MANAGE_EMPLOYEES','Manage Employees'),
('MANAGE_MAINTENANCE','Manage Maintenance'),
('MANAGE_LICENSES','Manage Licenses'),
('VIEW_REPORTS','View Reports'),
('EXPORT_REPORTS','Export Reports'),
('MANAGE_REQUESTS','Manage Requests'),
('MANAGE_ADMINS','Manage Admins'),
('VIEW_ACTIVITY_LOGS','View Activity Logs'),
('USE_AI_ASSISTANT','Use AI Assistant'),
('VIEW_NOTIFICATIONS','View Notifications');

-- SUPER_ADMIN gets everything
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name='SUPER_ADMIN'), id FROM permissions;

-- ADMIN gets everything except MANAGE_ADMINS by default (can be granted per-user later)
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name='ADMIN'), id FROM permissions
WHERE code <> 'MANAGE_ADMINS';

-- EMPLOYEE gets a minimal read/self-service set only
-- (No AI Assistant, No Notifications — per IMPORTANT ACCESS RULE)
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name='EMPLOYEE'), id FROM permissions
WHERE code IN ('VIEW_ASSETS','MANAGE_REQUESTS');

-- ------------------------------------------------------------
-- DEPARTMENTS
-- ------------------------------------------------------------
INSERT INTO departments (name, head_name) VALUES
('IT','Ravi Kumar'),
('HR','Ananya Sharma'),
('Finance','Suresh Iyer'),
('Operations','Priya Nair'),
('Sales','Vikram Singh');

-- ------------------------------------------------------------
-- DEMO USER ACCOUNTS
--   Admin    -> username: admin      password: Admin@123
--   Employee -> username: employee1  password: Employee@123
-- ------------------------------------------------------------
INSERT INTO users (full_name, username, email, phone, password_hash, employee_id, department_id, role_id, is_active)
VALUES
('System Administrator','admin','admin@company.com','9000000001',
 'scrypt:32768:8:1$p9mMG3tR8FYRneH2$f0ee1aeca91007378e5bbf720bacc481be5c1e7c7c476f0fe11869fa796b63a38ad987ef3f1080dfed384c9884950dd1102870ecb5f3844bd8c85c9d206d4b36',
 'ADM-001', 1, (SELECT id FROM roles WHERE name='SUPER_ADMIN'), 1),
('Employee One','employee1','employee1@company.com','9000000002',
 'scrypt:32768:8:1$n7pLcm3wE9zzJNuT$4ed8a547aa2eacf147aebf633286ecfc2825f7952fad52a533a0b82821e1885fed4af088f87cab73a05f7062ee12b91359852f975095b6d1f860e5116a4d8422',
 'EMP-001', 1, (SELECT id FROM roles WHERE name='EMPLOYEE'), 1);

-- ------------------------------------------------------------
-- EMPLOYEE PROFILES (linked + a few extra without login accounts)
-- ------------------------------------------------------------
INSERT INTO employees (user_id, employee_code, name, email, phone, department_id, designation, joining_date, status)
VALUES
((SELECT id FROM users WHERE username='employee1'), 'EMP-001', 'Employee One', 'employee1@company.com', '9000000002', 1, 'Software Engineer', '2023-01-15', 'ACTIVE');

INSERT INTO employees (employee_code, name, email, phone, department_id, designation, joining_date, status) VALUES
('EMP-002','Rahul Verma','rahul.verma@company.com','9000000003',1,'Network Engineer','2022-06-01','ACTIVE'),
('EMP-003','Sneha Reddy','sneha.reddy@company.com','9000000004',2,'HR Executive','2021-11-20','ACTIVE'),
('EMP-004','Amit Joshi','amit.joshi@company.com','9000000005',3,'Accountant','2020-03-10','ACTIVE'),
('EMP-005','Kavya Menon','kavya.menon@company.com','9000000006',4,'Operations Lead','2019-08-05','ACTIVE'),
('EMP-006','Arjun Nair','arjun.nair@company.com','9000000007',5,'Sales Executive','2023-09-01','ACTIVE');

-- ------------------------------------------------------------
-- ASSET CATEGORIES
-- ------------------------------------------------------------
INSERT INTO asset_categories (name, group_name) VALUES
('Laptop','IT'),('Desktop','IT'),('Monitor','IT'),('Keyboard','IT'),('Mouse','IT'),
('Printer','IT'),('Server','IT'),('Router','IT'),('Switch','IT'),('UPS','IT'),('Projector','IT'),
('Chair','OFFICE'),('Table','OFFICE'),('Cabinet','OFFICE'),('Air Conditioner','OFFICE'),
('Generator','ELECTRICAL'),('Inverter','ELECTRICAL'),
('Car','VEHICLE'),('Bike','VEHICLE'),('Van','VEHICLE');

-- ------------------------------------------------------------
-- ASSETS (realistic sample set across categories/departments/status)
-- ------------------------------------------------------------
INSERT INTO assets (asset_code, name, category_id, brand, model, serial_number, purchase_date, purchase_cost, current_value, warranty_start, warranty_end, vendor, department_id, location, assigned_employee_id, status, condition_status, description) VALUES
('LAP-1001','Dell Latitude 5440',(SELECT id FROM asset_categories WHERE name='Laptop'),'Dell','Latitude 5440','SN-DL5440-01','2023-02-10',65000,45000,'2023-02-10','2026-02-10','Dell India',1,'IT Office - 2nd Floor',(SELECT id FROM employees WHERE employee_code='EMP-002'),'ASSIGNED','GOOD','Company laptop for network engineer'),
('LAP-1002','HP ProBook 440',(SELECT id FROM asset_categories WHERE name='Laptop'),'HP','ProBook 440','SN-HP440-01','2022-05-14',58000,32000,'2022-05-14','2025-05-14','HP Store',1,'IT Office - 2nd Floor',NULL,'AVAILABLE','GOOD','Spare laptop'),
('LAP-1003','Lenovo ThinkPad E14',(SELECT id FROM asset_categories WHERE name='Laptop'),'Lenovo','ThinkPad E14','SN-LN14-01','2021-08-20',54000,20000,'2021-08-20','2024-08-20','Lenovo India',1,'IT Office',(SELECT id FROM employees WHERE employee_code='EMP-001'),'ASSIGNED','FAIR','Assigned to software engineer'),
('LAP-1004','Dell Latitude 5440 B',(SELECT id FROM asset_categories WHERE name='Laptop'),'Dell','Latitude 5440','SN-DL5440-02','2023-02-10',65000,45000,'2023-02-10','2026-02-10','Dell India',1,'IT Office',NULL,'AVAILABLE','GOOD','Spare unit'),
('DSK-2001','Dell OptiPlex 7010',(SELECT id FROM asset_categories WHERE name='Desktop'),'Dell','OptiPlex 7010','SN-OP7010-01','2020-01-15',48000,12000,'2020-01-15','2023-01-15','Dell India',3,'Finance Dept',(SELECT id FROM employees WHERE employee_code='EMP-004'),'ASSIGNED','FAIR','Finance workstation'),
('MON-3001','LG 24-inch Monitor',(SELECT id FROM asset_categories WHERE name='Monitor'),'LG','24MP400','SN-LG24-01','2022-03-01',9000,5000,'2022-03-01','2024-03-01','LG Electronics',1,'IT Office',NULL,'AVAILABLE','GOOD',NULL),
('PRN-4001','Canon LaserJet Pro',(SELECT id FROM asset_categories WHERE name='Printer'),'Canon','LBP2900','SN-CN29-01','2019-07-11',15000,3000,'2019-07-11','2021-07-11','Canon India',2,'HR Office',NULL,'UNDER_MAINTENANCE','POOR','Frequent paper jam issues'),
('SRV-5001','HP ProLiant DL380',(SELECT id FROM asset_categories WHERE name='Server'),'HP','ProLiant DL380','SN-PL380-01','2021-01-01',350000,220000,'2021-01-01','2026-01-01','HP Enterprise',1,'Server Room',NULL,'AVAILABLE','GOOD','Primary application server'),
('RTR-6001','Cisco ISR 4321',(SELECT id FROM asset_categories WHERE name='Router'),'Cisco','ISR 4321','SN-CS4321-01','2020-09-01',45000,18000,'2020-09-01','2023-09-01','Cisco Systems',1,'Server Room',NULL,'AVAILABLE','GOOD',NULL),
('UPS-7001','APC Smart-UPS 1500',(SELECT id FROM asset_categories WHERE name='UPS'),'APC','Smart-UPS 1500VA','SN-APC1500-01','2021-04-01',22000,9000,'2021-04-01','2023-04-01','APC India',1,'Server Room',NULL,'DAMAGED','POOR','Battery backup failing'),
('PRJ-8001','Epson EB-X06',(SELECT id FROM asset_categories WHERE name='Projector'),'Epson','EB-X06','SN-EPX06-01','2022-11-01',28000,20000,'2022-11-01','2024-11-01','Epson India',4,'Conference Room',NULL,'AVAILABLE','GOOD',NULL),
('CHR-9001','Ergonomic Office Chair',(SELECT id FROM asset_categories WHERE name='Chair'),'Featherlite','Ergo-200','SN-CHR-01','2021-06-01',8000,4000,NULL,NULL,'Featherlite',2,'HR Office',(SELECT id FROM employees WHERE employee_code='EMP-003'),'ASSIGNED','GOOD',NULL),
('GEN-1101','Diesel Generator 25KVA',(SELECT id FROM asset_categories WHERE name='Generator'),'Kirloskar','25KVA','SN-GEN-01','2019-02-01',450000,250000,'2019-02-01','2022-02-01','Kirloskar Oil Engines',4,'Facility Yard',NULL,'AVAILABLE','GOOD',NULL),
('CAR-1201','Toyota Innova',(SELECT id FROM asset_categories WHERE name='Car'),'Toyota','Innova Crysta','SN-CAR-01','2020-10-01',1800000,1200000,NULL,NULL,'Toyota Showroom',5,'Company Parking',(SELECT id FROM employees WHERE employee_code='EMP-006'),'ASSIGNED','GOOD','Sales team vehicle'),
('LAP-1005','MacBook Air M2',(SELECT id FROM asset_categories WHERE name='Laptop'),'Apple','MacBook Air M2','SN-MAC-01','2023-11-05',110000,95000,'2023-11-05','2025-11-05','Apple Store',4,'Ops Office',NULL,'RETIRED','POOR','Retired due to battery issues');

-- ------------------------------------------------------------
-- ASSET ASSIGNMENTS (history matching the ASSIGNED assets above)
-- ------------------------------------------------------------
INSERT INTO asset_assignments (asset_id, employee_id, department_id, assigned_date, expected_return_date, condition_before, notes, is_active) VALUES
((SELECT id FROM assets WHERE asset_code='LAP-1001'), (SELECT id FROM employees WHERE employee_code='EMP-002'), 1, '2023-02-15', NULL, 'GOOD', 'Issued at joining', 1),
((SELECT id FROM assets WHERE asset_code='LAP-1003'), (SELECT id FROM employees WHERE employee_code='EMP-001'), 1, '2023-01-20', NULL, 'GOOD', 'Issued for project work', 1),
((SELECT id FROM assets WHERE asset_code='DSK-2001'), (SELECT id FROM employees WHERE employee_code='EMP-004'), 3, '2020-02-01', NULL, 'NEW', 'Finance desktop setup', 1),
((SELECT id FROM assets WHERE asset_code='CHR-9001'), (SELECT id FROM employees WHERE employee_code='EMP-003'), 2, '2021-06-05', NULL, 'GOOD', NULL, 1),
((SELECT id FROM assets WHERE asset_code='CAR-1201'), (SELECT id FROM employees WHERE employee_code='EMP-006'), 5, '2023-09-05', NULL, 'GOOD', 'Sales vehicle allotment', 1);

-- ------------------------------------------------------------
-- MAINTENANCE RECORDS
-- ------------------------------------------------------------
INSERT INTO maintenance (asset_id, maintenance_type, problem, description, vendor, technician, start_date, expected_completion, actual_completion, cost, status, remarks) VALUES
((SELECT id FROM assets WHERE asset_code='PRN-4001'),'Repair','Paper jam / roller worn','Recurring paper jam, roller needs replacement','Canon Service Center','R. Prasad','2026-08-20','2026-09-05',NULL,2500,'IN_PROGRESS','Third repair visit this year'),
((SELECT id FROM assets WHERE asset_code='UPS-7001'),'Repair','Battery not holding charge','Battery replacement required','APC Authorized Service','S. Kumar','2026-08-25','2026-09-10',NULL,6000,'SCHEDULED',NULL),
((SELECT id FROM assets WHERE asset_code='LAP-1003'),'Preventive','Routine checkup','Annual health check and cleaning','Lenovo Service','A. Rao','2026-06-01','2026-06-03','2026-06-03',1200,'COMPLETED','No issues found'),
((SELECT id FROM assets WHERE asset_code='PRN-4001'),'Repair','Print quality issue','Toner and drum replacement','Canon Service Center','R. Prasad','2026-03-10','2026-03-12','2026-03-12',3200,'COMPLETED','Resolved'),
((SELECT id FROM assets WHERE asset_code='SRV-5001'),'Preventive','Quarterly maintenance','Firmware update and hardware check','HP Enterprise Support','V. Singh','2026-09-01','2026-09-02',NULL,15000,'SCHEDULED',NULL);

-- ------------------------------------------------------------
-- LICENSES
-- ------------------------------------------------------------
INSERT INTO licenses (software_name, license_key, license_type, vendor, purchase_date, start_date, expiry_date, cost, seats_total, seats_used, department_id, renewal_status, auto_renewal, notes) VALUES
('Microsoft 365 Business','MS365-XXXX-0001','Subscription','Microsoft','2025-10-01','2025-10-01','2026-10-01',45000,25,18,1,'OK',1,'Annual renewal'),
('Adobe Creative Cloud','ADB-XXXX-0002','Subscription','Adobe','2025-09-15','2025-09-15','2026-10-05',60000,5,4,4,'DUE_SOON',0,'Marketing team license'),
('Norton Antivirus','NRT-XXXX-0003','Perpetual+AMC','Norton','2025-01-10','2025-01-10','2026-09-20',12000,50,50,1,'DUE_SOON',1,'Company-wide antivirus'),
('AutoCAD 2024','ACAD-XXXX-0004','Subscription','Autodesk','2024-05-01','2024-05-01','2025-05-01',85000,3,3,4,'EXPIRED',0,'Needs renewal - operations team'),
('JetBrains All Products','JB-XXXX-0005','Subscription','JetBrains','2025-11-01','2025-11-01','2026-11-01',30000,10,7,1,'OK',1,'Developer tooling');

-- ------------------------------------------------------------
-- ASSET REQUESTS
-- ------------------------------------------------------------
INSERT INTO asset_requests (employee_id, category_id, reason, required_date, status, assigned_asset_id, admin_comment, handled_by) VALUES
((SELECT id FROM employees WHERE employee_code='EMP-003'), (SELECT id FROM asset_categories WHERE name='Laptop'), 'Current laptop is too slow for HR analytics work', '2026-09-15', 'PENDING', NULL, NULL, NULL),
((SELECT id FROM employees WHERE employee_code='EMP-005'), (SELECT id FROM asset_categories WHERE name='Monitor'), 'Need a second monitor for dashboards', '2026-09-20', 'APPROVED', (SELECT id FROM assets WHERE asset_code='MON-3001'), 'Approved - stock available', 1),
((SELECT id FROM employees WHERE employee_code='EMP-006'), (SELECT id FROM asset_categories WHERE name='Laptop'), 'New joiner in sales team needs a laptop', '2026-08-01', 'REJECTED', NULL, 'Budget approval pending for Q4', 1);

-- ------------------------------------------------------------
-- NOTIFICATIONS (admin-only)
-- ------------------------------------------------------------
INSERT INTO notifications (user_id, title, message, type, is_read) VALUES
(1,'License expiring soon','Adobe Creative Cloud expires on 2026-10-05','LICENSE_EXPIRY',0),
(1,'Maintenance overdue','Canon LaserJet Pro maintenance is in progress beyond expected date','MAINTENANCE',0),
(1,'New asset request','Sneha Reddy requested a Laptop','REQUEST',0);

-- ------------------------------------------------------------
-- ACTIVITY LOGS (sample historical entries)
-- ------------------------------------------------------------
INSERT INTO activity_logs (user_id, username, action, module, description, ip_address, status) VALUES
(1,'admin','LOGIN','AUTH','Admin logged in','127.0.0.1','SUCCESS'),
(1,'admin','ASSET_ADDED','ASSETS','Added asset LAP-1005 MacBook Air M2','127.0.0.1','SUCCESS'),
(1,'admin','ASSET_RETIRED','ASSETS','Retired asset LAP-1005 due to battery issues','127.0.0.1','SUCCESS'),
(2,'employee1','LOGIN','AUTH','Employee logged in','127.0.0.1','SUCCESS');
