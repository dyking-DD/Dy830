-- MASLAS 数据库初始化脚本
-- 创建时间: 2026-04-01

-- 创建数据库
CREATE DATABASE IF NOT EXISTS maslas_loan_system DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

USE maslas_loan_system;

-- 创建报单表
CREATE TABLE IF NOT EXISTS loan_applications (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_id VARCHAR(50) NOT NULL UNIQUE COMMENT '订单号',
    name VARCHAR(100) NOT NULL COMMENT '客户姓名',
    phone VARCHAR(20) NOT NULL COMMENT '联系电话',
    id_card VARCHAR(20) NOT NULL COMMENT '身份证号',
    salesperson VARCHAR(100) NOT NULL COMMENT '业务员姓名',
    car_model VARCHAR(100) NOT NULL COMMENT '车型',
    car_price DECIMAL(10, 2) NOT NULL COMMENT '车价（万元）',
    down_payment DECIMAL(10, 2) NOT NULL COMMENT '首付（万元）',
    loan_amount DECIMAL(10, 2) NOT NULL COMMENT '贷款金额（万元）',
    loan_term INT NOT NULL COMMENT '贷款期数',
    notes TEXT COMMENT '备注说明',
    submit_time DATETIME NOT NULL COMMENT '提交时间',
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' COMMENT '状态：待审批、已通过、已拒绝',
    risk_level ENUM('low', 'medium', 'high') COMMENT '风险等级：低、中、高',
    remarks TEXT COMMENT '审批备注',
    approval_time DATETIME COMMENT '审批时间',
    approver VARCHAR(100) COMMENT '审批人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_order_id (order_id),
    INDEX idx_salesperson (salesperson),
    INDEX idx_status (status),
    INDEX idx_submit_time (submit_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报单申请表';

-- 创建业务员表
CREATE TABLE IF NOT EXISTS salespersons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '业务员姓名',
    phone VARCHAR(20) NOT NULL UNIQUE COMMENT '联系电话',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='业务员表';

-- 创建风控规则表
CREATE TABLE IF NOT EXISTS risk_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL COMMENT '规则名称',
    rule_type ENUM('phone', 'id_card', 'amount', 'term', 'other') COMMENT '规则类型',
    rule_value VARCHAR(500) COMMENT '规则值',
    risk_level ENUM('low', 'medium', 'high') NOT NULL COMMENT '风险等级',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风控规则表';

-- 创建审批日志表
CREATE TABLE IF NOT EXISTS approval_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL COMMENT '订单号',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    operator VARCHAR(100) NOT NULL COMMENT '操作人',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审批日志表';

-- 创建通知表
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL COMMENT '订单号',
    recipient VARCHAR(100) NOT NULL COMMENT '接收人',
    type ENUM('new_order', 'approved', 'rejected', 'reminder') NOT NULL COMMENT '通知类型',
    title VARCHAR(200) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '内容',
    is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_recipient (recipient),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知表';

-- 插入示例风控规则
INSERT INTO risk_rules (rule_name, rule_type, rule_value, risk_level) VALUES
('身份证黑名单', 'id_card', '黑名单号码', 'high'),
('电话黑名单', 'phone', '黑名单号码', 'high'),
('贷款金额超过50万', 'amount', '>50', 'medium'),
('贷款期数超过60期', 'term', '>60', 'medium');

-- 插入示例业务员
INSERT INTO salespersons (name, phone) VALUES
('张业务员', '13800138001'),
('李业务员', '13800138002'),
('王业务员', '13800138003');

-- 创建视图：今日统计
CREATE OR REPLACE VIEW today_statistics AS
SELECT
    COUNT(*) as total_orders,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_orders,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders
FROM loan_applications
WHERE DATE(submit_time) = CURDATE();

-- 创建视图：业务员统计
CREATE OR REPLACE VIEW salesperson_statistics AS
SELECT
    salesperson,
    COUNT(*) as total_orders,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_orders,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders
FROM loan_applications
GROUP BY salesperson;

-- 输出初始化完成信息
SELECT 'MASLAS 数据库初始化完成！' AS message;
SELECT '数据库: maslas_loan_system' AS database_name;
SELECT '表: loan_applications, salespersons, risk_rules, approval_logs, notifications' AS tables;