"""
数据库连接和表创建模块
"""
import sqlite3
from datetime import datetime
from typing import Optional
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "car_loan.db")

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使用Row工厂，返回字典格式
    return conn

def init_database():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建订单表（完善版）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_phone TEXT,
            customer_id_number TEXT,
            car_brand TEXT,
            car_model TEXT,
            car_vin TEXT,
            car_plate_number TEXT,
            car_price REAL,
            stage TEXT NOT NULL DEFAULT '已接单',
            stage_remark TEXT,
            loan_amount REAL NOT NULL,
            down_payment REAL NOT NULL,
            loan_period INTEGER NOT NULL,
            monthly_payment REAL NOT NULL,
            interest_rate REAL,
            bank_name TEXT,
            advance_id TEXT,
            advance_amount REAL,
            advance_status TEXT,
            gps_device_id TEXT,
            gps_imei TEXT,
            gps_online_status TEXT,
            archive_status TEXT,
            archive_progress_percent INTEGER DEFAULT 0,
            created_by TEXT NOT NULL,
            created_at TEXT,
            stage_updated_at TEXT
        )
    """)
    
    # 创建还款计划表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repayment_plans (
            plan_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            period_number INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            due_amount REAL NOT NULL,
            actual_date TEXT,
            actual_amount REAL,
            status TEXT DEFAULT '正常',
            overdue_days INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)
    
    # 创建还款记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repayment_records (
            record_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            actual_amount REAL NOT NULL,
            repayment_date TEXT NOT NULL,
            payment_method TEXT,
            remark TEXT,
            created_at TEXT,
            FOREIGN KEY (plan_id) REFERENCES repayment_plans(plan_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)
    
    # 创建抵押登记表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mortgage (
            mortgage_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            mortgage_bank TEXT NOT NULL,
            register_date TEXT NOT NULL,
            expire_date TEXT NOT NULL,
            certificate_number TEXT,
            status TEXT DEFAULT '抵押中',
            release_date TEXT,
            created_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)
    
    conn.commit()
    conn.close()

def generate_id(prefix: str) -> str:
    """生成唯一ID（包含微秒级时间戳）"""
    import time
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # 添加微秒
    import random
    random_num = random.randint(100, 999)
    return f"{prefix}{timestamp}{random_num}"

# 应用启动时初始化数据库
init_database()
