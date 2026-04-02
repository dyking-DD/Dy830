# -*- coding: utf-8 -*-
"""
数据库初始化模块
使用 SQLite 数据库
"""
import sqlite3
import os
from pathlib import Path

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "notification.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    return conn


def init_database():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建通知日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            log_id TEXT PRIMARY KEY,
            order_id TEXT,
            channel TEXT NOT NULL,
            recipient TEXT NOT NULL,
            recipient_phone TEXT NOT NULL,
            template_code TEXT,
            content TEXT NOT NULL,
            status TEXT DEFAULT '待发送',
            sent_at TEXT,
            error_message TEXT,
            created_at TEXT
        )
    ''')
    
    # 创建通知模板表（虽然模板是内置的，但保留表结构以便扩展）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_templates (
            template_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            content_template TEXT NOT NULL,
            channel TEXT NOT NULL,
            remark TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")


if __name__ == "__main__":
    init_database()
