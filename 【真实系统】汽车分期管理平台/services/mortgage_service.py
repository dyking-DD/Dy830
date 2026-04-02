# -*- coding: utf-8 -*-
"""
抵押服务模块
处理抵押登记、解押等业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, generate_id


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


# ==================== 抵押服务 ====================

def create_mortgage(data: dict) -> dict:
    """
    创建抵押登记
    
    Args:
        data: 包含订单ID、抵押银行、登记日期等信息
        
    Returns:
        创建结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查订单是否存在
        cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (data.get("order_id"),))
        if not cursor.fetchone():
            return {"success": False, "message": "订单不存在"}
        
        # 检查是否已有抵押记录
        cursor.execute("SELECT mortgage_id FROM mortgage WHERE order_id = ? AND status = '抵押中'", (data.get("order_id"),))
        if cursor.fetchone():
            return {"success": False, "message": "该订单已有抵押中的记录"}
        
        # 生成抵押ID
        mortgage_id = generate_id("MTG")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 插入抵押记录
        cursor.execute("""
            INSERT INTO mortgage (
                mortgage_id, order_id, mortgage_bank, register_date,
                expire_date, certificate_number, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, '抵押中', ?)
        """, (
            mortgage_id, data.get("order_id"), data.get("mortgage_bank"),
            data.get("register_date"), data.get("expire_date"),
            data.get("certificate_number"), now
        ))
        
        # 更新订单阶段
        cursor.execute("""
            UPDATE orders SET stage = '已抵押', stage_updated_at = ?
            WHERE order_id = ?
        """, (now, data.get("order_id")))
        
        conn.commit()
        
        # 查询创建的抵押记录
        cursor.execute("""
            SELECT m.*, c.name as customer_name
            FROM mortgage m
            LEFT JOIN orders o ON m.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE m.mortgage_id = ?
        """, (mortgage_id,))
        
        mortgage = cursor.fetchone()
        
        return {
            "success": True,
            "message": "抵押登记成功",
            "data": row_to_dict(mortgage)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"登记失败: {str(e)}"}
    finally:
        conn.close()


def release_mortgage(order_id: str, release_date: str) -> dict:
    """
    解除抵押
    
    Args:
        order_id: 订单ID
        release_date: 解押日期
        
    Returns:
        解押结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询抵押记录
        cursor.execute("""
            SELECT * FROM mortgage WHERE order_id = ? AND status = '抵押中'
        """, (order_id,))
        
        mortgage = cursor.fetchone()
        if not mortgage:
            return {"success": False, "message": "抵押记录不存在或已解押"}
        
        # 更新抵押状态
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE mortgage SET status = '已解押', release_date = ?
            WHERE order_id = ? AND status = '抵押中'
        """, (release_date, order_id))
        
        # 更新订单状态为"已完结"
        cursor.execute("""
            UPDATE orders SET stage = '已完结', stage_updated_at = ?
            WHERE order_id = ?
        """, (now, order_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "解押成功",
            "data": {
                "order_id": order_id,
                "release_date": release_date,
                "status": "已解押"
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"解押失败: {str(e)}"}
    finally:
        conn.close()


def get_mortgage_list(order_id: str = None, status: str = None) -> dict:
    """
    获取抵押列表
    
    Args:
        order_id: 订单ID筛选
        status: 状态筛选
        
    Returns:
        抵押列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if order_id:
            conditions.append("m.order_id = ?")
            params.append(order_id)
        
        if status:
            conditions.append("m.status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f"""
            SELECT m.*, c.name as customer_name, c.phone as customer_phone,
                   v.brand as car_brand, v.model as car_model, v.plate_number
            FROM mortgage m
            LEFT JOIN orders o ON m.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE {where_clause}
            ORDER BY m.created_at DESC
        """, params)
        
        mortgages = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "data": {
                "total": len(mortgages),
                "items": mortgages
            }
        }
    finally:
        conn.close()


def get_mortgage_by_order(order_id: str) -> dict:
    """
    根据订单ID获取抵押详情
    
    Args:
        order_id: 订单ID
        
    Returns:
        抵押详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT m.*, c.name as customer_name, c.phone as customer_phone,
                   v.brand as car_brand, v.model as car_model, v.plate_number
            FROM mortgage m
            LEFT JOIN orders o ON m.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE m.order_id = ?
        """, (order_id,))
        
        mortgage = cursor.fetchone()
        
        if not mortgage:
            return {"success": False, "message": "抵押记录不存在"}
        
        return {
            "success": True,
            "data": row_to_dict(mortgage)
        }
    finally:
        conn.close()


def get_stats() -> dict:
    """
    获取抵押统计
    
    Returns:
        抵押统计数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 抵押总笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage")
        total = cursor.fetchone()["count"]
        
        # 抵押中笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage WHERE status = '抵押中'")
        mortgaged_count = cursor.fetchone()["count"]
        
        # 已解押笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage WHERE status = '已解押'")
        released_count = cursor.fetchone()["count"]
        
        # 30天内到期笔数
        today = datetime.now()
        expire_soon_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM mortgage
            WHERE status = '抵押中' AND expire_date <= ?
        """, (expire_soon_date,))
        expire_soon_count = cursor.fetchone()["count"]
        
        return {
            "success": True,
            "data": {
                "total": total,
                "mortgaged_count": mortgaged_count,
                "released_count": released_count,
                "expire_soon_count": expire_soon_count
            }
        }
    finally:
        conn.close()
