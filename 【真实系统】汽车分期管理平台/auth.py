# -*- coding: utf-8 -*-
"""
认证服务模块
汽车分期管理平台 - 用户认证与权限管理
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict


# 简单token：user_id + expiry 用hash签名
SECRET_KEY = "car_loan_platform_secret_key_2026"


def hash_password(password: str) -> str:
    """简单哈希，实际生产用werkzeug.security"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def generate_token(user_id: str, role: str, expiry_hours: int = 24) -> str:
    """生成简单token
    
    Args:
        user_id: 用户ID（管理员为user_id，客户为customer_id）
        role: 用户角色（admin/finance/collections/customer等）
        expiry_hours: 过期时间（小时）
    
    Returns:
        token字符串，格式：base64编码的user_id|role|expiry|signature
    """
    import base64
    
    expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
    raw = f"{user_id}|{role}|{expiry}|{SECRET_KEY}"
    signature = hashlib.sha256(raw.encode()).hexdigest()
    
    # 使用base64编码整个token
    token_data = f"{user_id}|{role}|{expiry}|{signature}"
    return base64.b64encode(token_data.encode()).decode()


def verify_token_full(token: str) -> Optional[Dict]:
    """完整验证token
    
    Args:
        token: token字符串
    
    Returns:
        验证成功返回包含user_id、role、expiry的字典，失败返回None
    """
    import base64
    
    try:
        # base64解码
        token_data = base64.b64decode(token.encode()).decode()
        parts = token_data.split("|")
        
        if len(parts) != 4:
            return None
        
        user_id, role, expiry, signature = parts
        
        # 检查是否过期
        expiry_dt = datetime.fromisoformat(expiry)
        if expiry_dt < datetime.now():
            return None  # token已过期
        
        # 验证签名
        raw = f"{user_id}|{role}|{expiry}|{SECRET_KEY}"
        expected_signature = hashlib.sha256(raw.encode()).hexdigest()
        if signature != expected_signature:
            return None  # 签名不匹配
        
        return {
            "user_id": user_id,
            "role": role,
            "expiry": expiry
        }
    except Exception as e:
        return None


def get_user_from_db(user_id: str, role: str) -> Optional[Dict]:
    """从数据库获取用户信息
    
    Args:
        user_id: 用户ID
        role: 用户角色
    
    Returns:
        用户信息字典，失败返回None
    """
    import database
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        if role == "customer":
            # 客户账户
            cursor.execute("""
                SELECT ca.account_id, ca.customer_id, ca.phone, ca.status,
                       c.name as customer_name
                FROM customer_accounts ca
                LEFT JOIN customers c ON ca.customer_id = c.customer_id
                WHERE ca.account_id = ? AND ca.status = '正常'
            """, (user_id,))
            user = cursor.fetchone()
            if user:
                return {
                    "user_id": user["account_id"],
                    "customer_id": user["customer_id"],
                    "role": "customer",
                    "name": user["customer_name"],
                    "phone": user["phone"]
                }
        else:
            # 管理员账户
            cursor.execute("""
                SELECT user_id, username, name, role, department, status
                FROM system_users
                WHERE user_id = ? AND status = '正常'
            """, (user_id,))
            user = cursor.fetchone()
            if user:
                return {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "name": user["name"],
                    "role": user["role"],
                    "department": user["department"]
                }
        return None
    finally:
        conn.close()
