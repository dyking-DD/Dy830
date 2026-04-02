# -*- coding: utf-8 -*-
"""
统一数据库模块
汽车分期管理平台 - 所有模块共享同一个SQLite数据库
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "car_loan_platform.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持字典式访问
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
    return conn


def generate_id(prefix: str) -> str:
    """生成唯一ID: PREFIX-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"{prefix}-{today}-{random_num}"


def init_database():
    """初始化数据库，创建所有表并插入测试数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ==================== 客户表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            id_number TEXT,
            address TEXT,
            created_at TEXT
        )
    """)
    
    # ==================== 车辆表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id TEXT PRIMARY KEY,
            order_id TEXT,
            brand TEXT,
            model TEXT,
            vin TEXT,
            plate_number TEXT,
            price REAL,
            created_at TEXT
        )
    """)
    
    # ==================== 订单表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            stage TEXT NOT NULL DEFAULT '已接单',
            stage_remark TEXT,
            loan_amount REAL NOT NULL,
            down_payment REAL NOT NULL,
            loan_period INTEGER NOT NULL,
            monthly_payment REAL NOT NULL,
            interest_rate REAL,
            bank_name TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT,
            stage_updated_at TEXT
        )
    """)
    
    # ==================== 垫资单表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advances (
            advance_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            advance_amount REAL NOT NULL,
            payer_type TEXT,
            payer_account TEXT,
            purpose TEXT,
            interest_rate REAL,
            start_date TEXT,
            expected_repayment_date TEXT,
            interest_amount REAL,
            total_amount REAL,
            status TEXT DEFAULT '待审批',
            approver TEXT,
            approver_opinion TEXT,
            approved_at TEXT,
            actual_repayment_date TEXT,
            repayment_amount REAL,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # ==================== GPS设备表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_devices (
            device_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            imei TEXT NOT NULL UNIQUE,
            device_type TEXT,
            install_location TEXT,
            install_staff TEXT,
            install_date TEXT,
            online_status TEXT DEFAULT '离线',
            last_heartbeat TEXT,
            current_location TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # ==================== GPS告警表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_alerts (
            alert_id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            alert_time TEXT,
            location TEXT,
            handled INTEGER DEFAULT 0,
            handled_by TEXT,
            handled_time TEXT,
            created_at TEXT
        )
    """)
    
    # ==================== 归档清单表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archive_checklists (
            checklist_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
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
    
    # ==================== 归档资料表 ====================
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
    
    # ==================== 还款计划表 ====================
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
            created_at TEXT
        )
    """)
    
    # ==================== 还款记录表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repayment_records (
            record_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            actual_amount REAL NOT NULL,
            repayment_date TEXT NOT NULL,
            payment_method TEXT,
            remark TEXT,
            created_at TEXT
        )
    """)
    
    # ==================== 抵押表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mortgage (
            mortgage_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            mortgage_bank TEXT NOT NULL,
            register_date TEXT,
            expire_date TEXT,
            certificate_number TEXT,
            status TEXT DEFAULT '抵押中',
            release_date TEXT,
            created_at TEXT
        )
    """)
    
    # ==================== 通知日志表 ====================
    cursor.execute("""
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
    """)
    
    # ==================== 系统用户表（后台管理员）====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT,
            status TEXT DEFAULT '正常',
            created_at TEXT
        )
    """)
    
    # ==================== 客户账户表（前台客户）====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_accounts (
            account_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            status TEXT DEFAULT '正常',
            created_at TEXT
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_stage ON orders(stage)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_advances_order ON advances(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_advances_status ON advances(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_devices_order ON gps_devices(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_alerts_device ON gps_alerts(device_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_checklists_order ON archive_checklists(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repayment_plans_order ON repayment_plans(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mortgage_order ON mortgage(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_logs_order ON notification_logs(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_accounts_customer ON customer_accounts(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_users_username ON system_users(username)")
    
    conn.commit()
    print(f"✅ 数据库表创建完成: {DB_PATH}")
    
    # ==================== 插入测试数据 ====================
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) as count FROM customers")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        print("ℹ️  测试数据已存在，跳过初始化")
        return
    
    print("📝 开始插入测试数据...")
    
    # 1. 插入3个客户
    customers = [
        ("CUS-001", "张三", "13800138001", "110101199001011234", "北京市朝阳区XX路XX号", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("CUS-002", "李四", "13800138002", "110101199002021234", "北京市海淀区XX路XX号", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("CUS-003", "王五", "13800138003", "110101199003031234", "北京市西城区XX路XX号", now.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO customers (customer_id, name, phone, id_number, address, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, customers)
    
    # 2. 插入3辆车（关联订单）
    vehicles = [
        ("VEH-001", "ORD-001", "宝马", "320Li", "LBV12345678901234", "京A12345", 350000.00, now.strftime("%Y-%m-%d %H:%M:%S")),
        ("VEH-002", "ORD-002", "奔驰", "C260L", "WDC12345678901234", "京B12345", 380000.00, now.strftime("%Y-%m-%d %H:%M:%S")),
        ("VEH-003", "ORD-003", "奥迪", "A4L", "WAU12345678901234", "京C12345", 320000.00, now.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO vehicles (vehicle_id, order_id, brand, model, vin, plate_number, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, vehicles)
    
    # 3. 插入3个订单（不同阶段）
    orders = [
        ("ORD-001", "CUS-001", "已提车", "GPS待安装", 280000.00, 70000.00, 36, 5833.33, 4.5, "工商银行", "系统管理员", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
        ("ORD-002", "CUS-002", "正常还款中", "", 300000.00, 80000.00, 36, 6111.11, 4.5, "建设银行", "系统管理员", (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"), (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")),
        ("ORD-003", "CUS-003", "已接单", "待垫资审批", 250000.00, 70000.00, 24, 7500.00, 4.8, "招商银行", "系统管理员", (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO orders (order_id, customer_id, stage, stage_remark, loan_amount, down_payment, loan_period, monthly_payment, interest_rate, bank_name, created_by, created_at, stage_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders)
    
    # 4. 插入2个垫资单
    advances = [
        ("DZ-001", "ORD-001", 50000.00, "公司垫资", "公司账户", "垫资购车", 0.05, now.strftime("%Y-%m-%d"), (now + timedelta(days=30)).strftime("%Y-%m-%d"), 0, 50000.00, "已出账", "审批员A", "同意垫资", now.strftime("%Y-%m-%d %H:%M:%S"), None, None, "业务员A", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
        ("DZ-002", "ORD-002", 60000.00, "公司垫资", "公司账户", "垫资购车", 0.05, (now - timedelta(days=90)).strftime("%Y-%m-%d"), (now - timedelta(days=60)).strftime("%Y-%m-%d"), 900.00, 60900.00, "已还清", "审批员B", "同意垫资", (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"), (now - timedelta(days=60)).strftime("%Y-%m-%d"), 60900.00, "业务员B", (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"), (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO advances (advance_id, order_id, advance_amount, payer_type, payer_account, purpose, interest_rate, start_date, expected_repayment_date, interest_amount, total_amount, status, approver, approver_opinion, approved_at, actual_repayment_date, repayment_amount, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, advances)
    
    # 5. 插入2个GPS设备
    gps_devices = [
        ("GPS-0001-0001", "ORD-001", "123456789012345", "有线", "驾驶座下方", "张师傅", now.strftime("%Y-%m-%d"), "在线", now.strftime("%Y-%m-%d %H:%M:%S"), "北京市朝阳区", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
        ("GPS-0002-0002", "ORD-002", "123456789012346", "无线", "后备箱", "李师傅", (now - timedelta(days=60)).strftime("%Y-%m-%d"), "在线", now.strftime("%Y-%m-%d %H:%M:%S"), "北京市海淀区", (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO gps_devices (device_id, order_id, imei, device_type, install_location, install_staff, install_date, online_status, last_heartbeat, current_location, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, gps_devices)
    
    # 6. 插入1个归档清单
    cursor.execute("""
        INSERT INTO archive_checklists (checklist_id, order_id, id_card_front, id_card_back, driving_license, vehicle_certificate, gps_photos, pickup_confirmation, advance_agreement, invoice, insurance, overall_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("CL-001", "ORD-001", 1, 1, 1, 1, 0, 1, 1, 0, 0, "部分上传", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")))
    
    # 7. 插入还款计划（ORD-002的36期）
    repayment_plans = []
    start_date = datetime.now() - timedelta(days=60)
    for i in range(36):
        due_date = start_date + relativedelta(months=i)
        plan_id = f"RPP-{today}-{str(i+1).zfill(4)}"
        status = "已还清" if i < 3 else "正常"
        actual_date = due_date.strftime("%Y-%m-%d") if i < 3 else None
        actual_amount = 6111.11 if i < 3 else None
        repayment_plans.append((plan_id, "ORD-002", i+1, due_date.strftime("%Y-%m-%d"), 6111.11, actual_date, actual_amount, status, now.strftime("%Y-%m-%d %H:%M:%S")))
    
    cursor.executemany("""
        INSERT INTO repayment_plans (plan_id, order_id, period_number, due_date, due_amount, actual_date, actual_amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, repayment_plans)
    
    # 8. 插入抵押记录
    cursor.execute("""
        INSERT INTO mortgage (mortgage_id, order_id, mortgage_bank, register_date, expire_date, certificate_number, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("MTG-001", "ORD-002", "工商银行", (now - timedelta(days=60)).strftime("%Y-%m-%d"), (now + timedelta(days=365*3)).strftime("%Y-%m-%d"), "BJ2024001", "抵押中", (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")))
    
    # 9. 插入系统用户（后台管理员）
    import hashlib
    def hash_pwd(pwd: str) -> str:
        return hashlib.sha256(pwd.encode()).hexdigest()
    
    system_users = [
        ("USER-0001", "admin", hash_pwd("admin123"), "系统管理员", "admin", None, "正常", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-0002", "finance01", hash_pwd("finance123"), "财务张", "finance", "财务部", "正常", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-0003", "collections01", hash_pwd("collect123"), "贷后李", "collections", "贷后部", "正常", now.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO system_users (user_id, username, password_hash, name, role, department, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, system_users)
    
    # 10. 插入客户账户（前台客户）
    customer_accounts = [
        ("ACC-0001", "CUS-001", "13800138001", hash_pwd("123456"), "正常", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("ACC-0002", "CUS-002", "13800138002", hash_pwd("123456"), "正常", now.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    cursor.executemany("""
        INSERT INTO customer_accounts (account_id, customer_id, phone, password_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, customer_accounts)
    
    conn.commit()
    conn.close()
    print("✅ 测试数据插入完成")


if __name__ == "__main__":
    init_database()
