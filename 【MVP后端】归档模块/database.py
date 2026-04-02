"""
数据库连接和表创建模块
归档模块使用 SQLite 数据库进行数据存储
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "archive_management.db"


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
    
    # 创建归档清单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archive_checklists (
            checklist_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL UNIQUE,
            customer_name TEXT,
            id_card_front INTEGER DEFAULT 0,
            id_card_back INTEGER DEFAULT 0,
            driving_license INTEGER DEFAULT 0,
            vehicle_certificate INTEGER DEFAULT 0,
            gps_photos INTEGER DEFAULT 0,
            pickup_confirmation INTEGER DEFAULT 0,
            advance_agreement INTEGER DEFAULT 0,
            invoice INTEGER DEFAULT 0,
            insurance INTEGER DEFAULT 0,
            overall_status TEXT DEFAULT '待上传',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 创建归档资料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archive_documents (
            document_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_url TEXT NOT NULL,
            ocr_result TEXT,
            upload_time TEXT,
            uploaded_by TEXT
        )
    """)
    
    # 创建订单表（简化版，用于测试归档功能）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            car_model TEXT,
            status TEXT DEFAULT 'pending',
            pickup_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklists_order ON archive_checklists(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklists_status ON archive_checklists(overall_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_order ON archive_documents(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON archive_documents(document_type)")
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


# 在模块导入时初始化数据库
init_database()
