"""
数据库连接和表创建模块
使用 SQLite 数据库进行数据存储
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "advance_management.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持字典式访问
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
    return conn


def init_database():
    """初始化数据库，创建所有表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建订单表（简化版，用于测试垫资功能）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            car_model TEXT,
            car_price DECIMAL(12, 2),
            down_payment DECIMAL(12, 2),
            loan_amount DECIMAL(12, 2),
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建垫资单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advance_no TEXT UNIQUE NOT NULL,
            order_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            amount DECIMAL(12, 2) NOT NULL,
            lender_type TEXT NOT NULL CHECK(lender_type IN ('company', 'personal')),
            lender_account TEXT NOT NULL,
            purpose TEXT,
            interest_rate_type TEXT NOT NULL CHECK(interest_rate_type IN ('monthly', 'daily')),
            monthly_rate DECIMAL(5, 4) DEFAULT 0.015,
            daily_rate DECIMAL(7, 6),
            start_date DATE NOT NULL,
            expected_repay_date DATE NOT NULL,
            actual_repay_date DATE,
            actual_repay_amount DECIMAL(12, 2),
            calculated_interest DECIMAL(12, 2),
            status TEXT NOT NULL DEFAULT 'pending_approval' CHECK(status IN (
                'pending_approval',
                'approved',
                'rejected',
                'disbursed',
                'repaid',
                'overdue'
            )),
            approver TEXT,
            approval_opinion TEXT,
            approval_time TIMESTAMP,
            disburse_time TIMESTAMP,
            repay_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    # 创建垫资余额趋势记录表（用于仪表盘）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advance_balance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date DATE NOT NULL UNIQUE,
            total_balance DECIMAL(12, 2) NOT NULL,
            advance_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_advances_status ON advances(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_advances_start_date ON advances(start_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_advances_customer ON advances(customer_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_name)")
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


# 在模块导入时初始化数据库
init_database()
