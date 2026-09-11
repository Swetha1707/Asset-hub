-- ============================================================
-- AI-Integrated Asset Management System — MySQL Schema
-- Run: mysql -u root -p < database/schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS asset_management
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE asset_management;

-- ------------------------------------------------------------
-- ROLES & PERMISSIONS
-- ------------------------------------------------------------
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE   -- SUPER_ADMIN, ADMIN, EMPLOYEE
);

CREATE TABLE permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(60) NOT NULL UNIQUE,   -- e.g. VIEW_ASSETS
    label VARCHAR(120) NOT NULL
);

CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- Per-user permission overrides (used for individually-created ADMIN accounts)
CREATE TABLE user_permissions (
    user_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (user_id, permission_id),
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- DEPARTMENTS
-- ------------------------------------------------------------
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    head_name VARCHAR(120),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- USERS (login accounts: super admin / admin / employee)
-- ------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    username VARCHAR(60) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(30),
    password_hash VARCHAR(255) NOT NULL,
    employee_id VARCHAR(30) UNIQUE,
    department_id INT,
    role_id INT NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    profile_image VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- ------------------------------------------------------------
-- EMPLOYEES (extended HR-style profile; 1:1 with a user account
-- for EMPLOYEE role, but kept separate so assets can be assigned
-- to people even before/without a login account)
-- ------------------------------------------------------------
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE,
    employee_code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(30),
    department_id INT,
    designation VARCHAR(100),
    joining_date DATE,
    status ENUM('ACTIVE','INACTIVE') DEFAULT 'ACTIVE',
    profile_image VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- ASSET CATEGORIES
-- ------------------------------------------------------------
CREATE TABLE asset_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    group_name VARCHAR(50)  -- IT / OFFICE / ELECTRICAL / VEHICLE / OTHER
);

-- ------------------------------------------------------------
-- ASSETS
-- ------------------------------------------------------------
CREATE TABLE assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    category_id INT,
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100) UNIQUE,
    purchase_date DATE,
    purchase_cost DECIMAL(12,2) DEFAULT 0,
    current_value DECIMAL(12,2) DEFAULT 0,
    warranty_start DATE,
    warranty_end DATE,
    vendor VARCHAR(150),
    department_id INT,
    location VARCHAR(150),
    assigned_employee_id INT,
    status ENUM('AVAILABLE','ASSIGNED','RESERVED','UNDER_MAINTENANCE','LOST','DAMAGED','RETIRED','DISPOSED') DEFAULT 'AVAILABLE',
    condition_status ENUM('NEW','GOOD','FAIR','POOR') DEFAULT 'NEW',
    description TEXT,
    image_path VARCHAR(255),
    is_deleted TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES asset_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_employee_id) REFERENCES employees(id) ON DELETE SET NULL,
    INDEX idx_assets_status (status),
    INDEX idx_assets_department (department_id),
    INDEX idx_assets_category (category_id)
);

CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- ASSIGNMENTS & RETURNS
-- ------------------------------------------------------------
CREATE TABLE asset_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL,
    employee_id INT NOT NULL,
    department_id INT,
    assigned_date DATE NOT NULL,
    expected_return_date DATE,
    condition_before VARCHAR(50),
    notes TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

CREATE TABLE asset_returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    asset_id INT NOT NULL,
    return_date DATE NOT NULL,
    condition_after VARCHAR(50),
    damage_notes TEXT,
    accessories_returned VARCHAR(255),
    verified_by INT,
    remarks TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES asset_assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
CREATE TABLE return_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    asset_id INT NOT NULL,
    reason TEXT,
    status ENUM('PENDING','APPROVED','REJECTED','COMPLETED')
           DEFAULT 'PENDING',
    admin_comment TEXT,
    handled_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(id)
        ON DELETE CASCADE,

    FOREIGN KEY (asset_id)
        REFERENCES assets(id)
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- REQUESTS
-- ------------------------------------------------------------
CREATE TABLE asset_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    category_id INT,
    reason TEXT,
    required_date DATE,
    status ENUM('PENDING','APPROVED','REJECTED','ISSUED','RETURNED','CANCELLED') DEFAULT 'PENDING',
    assigned_asset_id INT,
    admin_comment TEXT,
    handled_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES asset_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_asset_id) REFERENCES assets(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- MAINTENANCE
-- ------------------------------------------------------------
CREATE TABLE maintenance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL,
    maintenance_type VARCHAR(100),
    problem VARCHAR(255),
    description TEXT,
    vendor VARCHAR(150),
    technician VARCHAR(120),
    start_date DATE,
    expected_completion DATE,
    actual_completion DATE,
    cost DECIMAL(12,2) DEFAULT 0,
    status ENUM('SCHEDULED','IN_PROGRESS','COMPLETED','CANCELLED') DEFAULT 'SCHEDULED',
    remarks TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    INDEX idx_maintenance_status (status)
);
CREATE TABLE maintenance_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    asset_id INT NOT NULL,
    problem VARCHAR(255) NOT NULL,
    description TEXT,

    status ENUM(
        'PENDING',
        'APPROVED',
        'REJECTED',
        'IN_PROGRESS',
        'COMPLETED'
    ) DEFAULT 'PENDING',

    admin_comment TEXT,
    handled_by INT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(id)
        ON DELETE CASCADE,

    FOREIGN KEY (asset_id)
        REFERENCES assets(id)
        ON DELETE CASCADE
);
-- ------------------------------------------------------------
-- LICENSES & SUBSCRIPTIONS
-- ------------------------------------------------------------
CREATE TABLE licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    software_name VARCHAR(150) NOT NULL,
    license_key VARCHAR(255),
    license_type VARCHAR(80),
    vendor VARCHAR(150),
    purchase_date DATE,
    start_date DATE,
    expiry_date DATE,
    cost DECIMAL(12,2) DEFAULT 0,
    seats_total INT DEFAULT 1,
    seats_used INT DEFAULT 0,
    department_id INT,
    renewal_status ENUM('OK','DUE_SOON','EXPIRED') DEFAULT 'OK',
    auto_renewal TINYINT(1) DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    INDEX idx_license_expiry (expiry_date)
);

CREATE TABLE license_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id INT NOT NULL,
    employee_id INT NOT NULL,
    assigned_date DATE DEFAULT (CURRENT_DATE),
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- NOTIFICATIONS (admin-only, per IMPORTANT ACCESS RULE)
-- ------------------------------------------------------------
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,          -- recipient (must be SUPER_ADMIN/ADMIN)
    title VARCHAR(150) NOT NULL,
    message VARCHAR(500),
    type VARCHAR(50),
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notif_user (user_id, is_read)
);

-- ------------------------------------------------------------
-- ACTIVITY / AUDIT LOGS
-- ------------------------------------------------------------
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(60),
    action VARCHAR(100) NOT NULL,
    module VARCHAR(60),
    description VARCHAR(500),
    ip_address VARCHAR(64),
    status VARCHAR(20) DEFAULT 'SUCCESS',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_log_user (user_id),
    INDEX idx_log_module (module),
    INDEX idx_log_date (created_at)
);
