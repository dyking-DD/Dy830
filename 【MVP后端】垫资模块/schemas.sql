-- ========================================
-- 汽车分期管理平台 - 垫资管理模块
-- 数据库建表 SQL（备用）
-- ========================================

-- 订单表（简化版，用于测试垫资功能）
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,                     -- 订单号
    customer_name TEXT NOT NULL,                       -- 客户姓名
    customer_phone TEXT,                               -- 客户电话
    car_model TEXT,                                    -- 车型
    car_price DECIMAL(12, 2),                         -- 车辆价格
    down_payment DECIMAL(12, 2),                      -- 首付金额
    loan_amount DECIMAL(12, 2),                       -- 贷款金额
    status TEXT DEFAULT 'pending',                     -- 订单状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- 更新时间
);

-- 垫资单表
CREATE TABLE IF NOT EXISTS advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_no TEXT UNIQUE NOT NULL,                   -- 垫资单号（格式：DZ-YYYYMMDD-XXXX）
    order_id INTEGER NOT NULL,                         -- 关联订单ID
    customer_name TEXT NOT NULL,                       -- 客户姓名
    amount DECIMAL(12, 2) NOT NULL,                   -- 垫资金额
    lender_type TEXT NOT NULL CHECK(lender_type IN ('company', 'personal')),  -- 垫资方类型
    lender_account TEXT NOT NULL,                      -- 垫资账户
    purpose TEXT,                                      -- 垫资用途
    interest_rate_type TEXT NOT NULL CHECK(interest_rate_type IN ('monthly', 'daily')),  -- 利率类型
    monthly_rate DECIMAL(5, 4) DEFAULT 0.015,         -- 月利率，默认1.5%
    daily_rate DECIMAL(7, 6),                         -- 日利率
    start_date DATE NOT NULL,                          -- 垫资开始日期
    expected_repay_date DATE NOT NULL,                 -- 预计还款日期
    actual_repay_date DATE,                            -- 实际还款日期
    actual_repay_amount DECIMAL(12, 2),               -- 实际还款金额
    calculated_interest DECIMAL(12, 2),               -- 计算利息
    status TEXT NOT NULL DEFAULT 'pending_approval' CHECK(status IN (
        'pending_approval',  -- 待审批
        'approved',          -- 审批通过
        'rejected',          -- 审批拒绝
        'disbursed',         -- 已出账
        'repaid',            -- 已还清
        'overdue'            -- 逾期
    )),
    approver TEXT,                                     -- 审批人
    approval_opinion TEXT,                             -- 审批意见
    approval_time TIMESTAMP,                           -- 审批时间
    disburse_time TIMESTAMP,                           -- 出账时间
    repay_time TIMESTAMP,                              -- 还款时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    -- 更新时间
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- 垫资余额趋势记录表（用于仪表盘）
CREATE TABLE IF NOT EXISTS advance_balance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date DATE NOT NULL UNIQUE,                  -- 记录日期
    total_balance DECIMAL(12, 2) NOT NULL,            -- 当日垫资余额
    advance_count INTEGER NOT NULL,                    -- 当日垫资笔数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- 创建时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_advances_status ON advances(status);
CREATE INDEX IF NOT EXISTS idx_advances_start_date ON advances(start_date);
CREATE INDEX IF NOT EXISTS idx_advances_customer ON advances(customer_name);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_name);
CREATE INDEX IF NOT EXISTS idx_balance_history_date ON advance_balance_history(record_date);

-- ========================================
-- 示例数据（可选）
-- ========================================

-- 插入测试订单
-- INSERT INTO orders (order_no, customer_name, customer_phone, car_model, car_price, down_payment, loan_amount, status)
-- VALUES 
--     ('DD-20240101-0001', '张三', '13800138001', '特斯拉 Model 3', 280000.00, 84000.00, 196000.00, 'pending'),
--     ('DD-20240101-0002', '李四', '13800138002', '比亚迪 汉', 220000.00, 66000.00, 154000.00, 'pending');

-- 插入测试垫资单
-- INSERT INTO advances (
--     advance_no, order_id, customer_name, amount, lender_type, lender_account, purpose,
--     interest_rate_type, monthly_rate, daily_rate, start_date, expected_repay_date, status
-- ) VALUES 
--     ('DZ-20240101-0001', 1, '张三', 50000.00, 'company', '公司账户A', '首付垫资',
--      'monthly', 0.015, 0.0005, '2024-01-01', '2024-02-01', 'pending_approval'),
--     ('DZ-20240101-0002', 2, '李四', 30000.00, 'personal', '个人账户B', '临时周转',
--      'daily', NULL, 0.0008, '2024-01-01', '2024-01-15', 'pending_approval');

-- ========================================
-- 查询示例
-- ========================================

-- 查询当前垫资余额（所有未还清垫资单的本金之和）
-- SELECT COALESCE(SUM(amount), 0) as current_balance
-- FROM advances
-- WHERE status IN ('disbursed', 'overdue');

-- 查询逾期垫资单
-- SELECT * FROM advances
-- WHERE status = 'disbursed'
--   AND expected_repay_date < DATE('now');

-- 计算垫资利息
-- 利息 = 垫资金额 × 日利率 × 实际天数
-- 日利率 = 月利率 / 30
-- 
-- 示例：
-- 垫资金额：50000元
-- 月利率：1.5%
-- 日利率：0.015 / 30 = 0.0005
-- 实际天数：30天
-- 利息 = 50000 × 0.0005 × 30 = 750元
