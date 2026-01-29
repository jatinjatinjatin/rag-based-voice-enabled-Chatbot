-- ============================
-- PROJECTS
-- ============================
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT,
    owner TEXT,
    start_date TEXT,
    end_date TEXT,
    budget REAL
);

INSERT INTO projects VALUES
(1, 'Website Redesign', 'Alice', '2023-01-01', '2023-06-01', 50000),
(2, 'Mobile App', 'Bob', '2023-02-15', NULL, 120000),
(3, 'AI Research', 'Charlie', NULL, NULL, 200000),
(4, 'CRM Upgrade', 'Diana', '2023-03-10', '2023-09-30', NULL),
(5, 'Security Audit', 'Evan', '2023-04-01', NULL, 30000);

-- ============================
-- TASKS
-- ============================
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title TEXT,
    status TEXT,
    assigned_to TEXT,
    due_date TEXT
);

INSERT INTO tasks VALUES
(1, 1, 'Design UI', 'Completed', 'John', '2023-02-15'),
(2, 1, 'Implement frontend', 'In Progress', 'Maria', NULL),
(3, 2, 'API development', 'Pending', 'Rahul', '2023-05-01'),
(4, 3, 'Model training', NULL, 'Li', '2023-08-01'),
(5, 4, 'Database migration', 'Completed', NULL, '2023-07-15');

-- ============================
-- ASSETS
-- ============================
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    purchase_date TEXT,
    value REAL,
    assigned_to TEXT
);

INSERT INTO assets VALUES
(1, 'Laptop Dell', 'Hardware', '2022-01-10', 1200, 'Alice'),
(2, 'Office Chair', 'Furniture', '2021-05-20', 300, NULL),
(3, 'Server Rack', 'Hardware', NULL, 8000, 'IT Dept'),
(4, 'Projector', NULL, '2020-11-11', 1500, 'Conference Room'),
(5, 'Router', 'Networking', '2023-02-02', NULL, 'IT Dept');

-- ============================
-- LOGS
-- ============================
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY,
    service_name TEXT,
    log_level TEXT,
    message TEXT,
    created_at TEXT
);

INSERT INTO system_logs VALUES
(1, 'AuthService', 'INFO', 'User login successful', '2024-01-01 10:00'),
(2, 'PaymentService', 'ERROR', 'Transaction failed', '2024-01-02 12:30'),
(3, 'InventoryService', 'WARN', NULL, '2024-01-03 14:15'),
(4, 'API Gateway', NULL, 'Timeout occurred', '2024-01-04 09:45'),
(5, 'Scheduler', 'INFO', 'Job executed', NULL);

-- ============================
-- SUPPORT_TICKETS
-- ============================
CREATE TABLE support_tickets (
    id INTEGER PRIMARY KEY,
    user_name TEXT,
    issue_type TEXT,
    priority TEXT,
    status TEXT,
    resolution_time_hours REAL
);

INSERT INTO support_tickets VALUES
(1, 'Alice', 'Login Issue', 'High', 'Resolved', 2),
(2, 'Bob', 'Payment Error', 'Medium', 'Open', NULL),
(3, 'Charlie', 'UI Bug', NULL, 'Resolved', 5),
(4, 'Diana', 'Data Sync', 'Low', NULL, NULL),
(5, 'Evan', 'Report Export', 'Medium', 'Resolved', 1.5);

-- ============================
-- API_USAGE
-- ============================
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY,
    api_name TEXT,
    client_name TEXT,
    request_count INTEGER,
    error_count INTEGER,
    last_used TEXT
);

INSERT INTO api_usage VALUES
(1, 'Auth API', 'WebApp', 12000, 25, '2024-01-05'),
(2, 'Payment API', 'MobileApp', 8000, NULL, '2024-01-04'),
(3, 'Orders API', 'PartnerService', NULL, 10, '2024-01-03'),
(4, 'Analytics API', NULL, 5000, 0, '2024-01-02'),
(5, 'Search API', 'WebApp', 15000, 50, NULL);

-- ============================
-- METRICS
-- ============================
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    metric_name TEXT,
    value REAL,
    unit TEXT,
    recorded_at TEXT
);

INSERT INTO metrics VALUES
(1, 'CPU_Usage', 65.5, '%', '2024-01-01'),
(2, 'Memory_Usage', 72.3, '%', '2024-01-01'),
(3, 'Disk_IO', NULL, 'MB/s', '2024-01-01'),
(4, 'Response_Time', 250, 'ms', NULL),
(5, 'Active_Users', 1200, NULL, '2024-01-01');

-- ============================
-- NOTIFICATIONS
-- ============================
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    user_name TEXT,
    channel TEXT,
    message TEXT,
    sent_at TEXT,
    read_status TEXT
);

INSERT INTO notifications VALUES
(1, 'Alice', 'Email', 'Password changed', '2024-01-01', 'Read'),
(2, 'Bob', 'SMS', 'Payment received', '2024-01-02', NULL),
(3, 'Charlie', 'Push', NULL, '2024-01-03', 'Unread'),
(4, 'Diana', NULL, 'System update available', '2024-01-04', 'Read'),
(5, 'Evan', 'Email', 'New login detected', NULL, 'Unread');

-- ============================
-- CONFIG_SETTINGS
-- ============================
CREATE TABLE config_settings (
    id INTEGER PRIMARY KEY,
    config_key TEXT,
    config_value TEXT,
    environment TEXT,
    last_updated TEXT
);

INSERT INTO config_settings VALUES
(1, 'MAX_LOGIN_ATTEMPTS', '5', 'production', '2024-01-01'),
(2, 'ENABLE_CACHE', 'true', 'staging', '2024-01-02'),
(3, 'API_TIMEOUT', NULL, 'production', '2024-01-03'),
(4, 'LOG_LEVEL', 'DEBUG', NULL, '2024-01-04'),
(5, 'FEATURE_X_ENABLED', 'false', 'development', NULL);
