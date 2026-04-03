# -*- coding: utf-8 -*-
"""
垫资服务模块
处理垫资单的创建、审批、出账、还款等业务逻辑
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import sys
import os

# 添加父目录到路径，以便导入database模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, generate_id


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


# ==================== 状态机定义 ====================

# 垫资单状态流转规则
ADVANCE_STATUS_TRANSITIONS = {
    "待审批": ["已审批", "已拒绝"],
    "已审批": ["已出账"],
    "已出账": ["已还清", "逾期"],
    "逾期": ["已还清"],
    "已拒绝": [],  # 终态
    "已还清": [],  # 终态
}


def can_transition(current_status: str, new_status: str) -> bool:
    """检查状态流转是否合法"""
    allowed = ADVANCE_STATUS_TRANSITIONS.get(current_status, [])
    return new_status in allowed


# ==================== 垫资单服务 ====================

def create_advance(data: dict) -> dict:
    """
    创建垫资单
    
    Args:
        data: 包含订单ID、垫资金额、利率、日期等信息
        
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
        
        # 生成垫资单ID
        advance_id = generate_id("DZ")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 计算利息和总金额
        advance_amount = Decimal(str(data.get("advance_amount", 0)))
        interest_rate = Decimal(str(data.get("interest_rate", 0)))
        
        cursor.execute("""
            INSERT INTO advances (
                advance_id, order_id, advance_amount, payer_type, payer_account,
                purpose, interest_rate, start_date, expected_repayment_date,
                status, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            advance_id, data.get("order_id"), float(advance_amount),
            data.get("payer_type"), data.get("payer_account"), data.get("purpose"),
            float(interest_rate), data.get("start_date"), data.get("expected_repayment_date"),
            "待审批", data.get("created_by"), now, now
        ))
        
        conn.commit()
        
        # 查询创建的垫资单
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        advance = cursor.fetchone()
        
        return {
            "success": True,
            "message": "垫资单创建成功",
            "data": row_to_dict(advance)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"创建失败: {str(e)}"}
    finally:
        conn.close()


def approve_advance(advance_id: str, approver: str, opinion: str, approved: bool) -> dict:
    """
    审批垫资单
    
    Args:
        advance_id: 垫资单ID
        approver: 审批人
        opinion: 审批意见
        approved: 是否通过
        
    Returns:
        审批结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        advance = cursor.fetchone()
        
        if not advance:
            return {"success": False, "message": "垫资单不存在"}
        
        advance_dict = row_to_dict(advance)
        current_status = advance_dict["status"]
        
        # 检查状态
        if current_status != "待审批":
            return {"success": False, "message": f"当前状态【{current_status}】不可审批"}
        
        # 更新状态
        new_status = "已审批" if approved else "已拒绝"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE advances
            SET status = ?, approver = ?, approver_opinion = ?, approved_at = ?, updated_at = ?
            WHERE advance_id = ?
        """, (new_status, approver, opinion, now, now, advance_id))
        
        conn.commit()
        
        # 查询更新后的垫资单
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        updated = cursor.fetchone()
        
        return {
            "success": True,
            "message": f"审批{'通过' if approved else '拒绝'}",
            "data": row_to_dict(updated)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"审批失败: {str(e)}"}
    finally:
        conn.close()


def disburse_advance(advance_id: str, disburse_by: str) -> dict:
    """
    垫资出账
    
    Args:
        advance_id: 垫资单ID
        disburse_by: 出账人
        
    Returns:
        出账结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        advance = cursor.fetchone()
        
        if not advance:
            return {"success": False, "message": "垫资单不存在"}
        
        advance_dict = row_to_dict(advance)
        current_status = advance_dict["status"]
        
        # 检查状态
        if current_status != "已审批":
            return {"success": False, "message": f"当前状态【{current_status}】不可出账"}
        
        # 更新状态
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE advances
            SET status = '已出账', updated_at = ?
            WHERE advance_id = ?
        """, (now, advance_id))
        
        # 更新订单阶段
        cursor.execute("""
            UPDATE orders
            SET stage = '垫资已出账', stage_updated_at = ?
            WHERE order_id = ?
        """, (now, advance_dict["order_id"]))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "出账成功",
            "data": {"advance_id": advance_id, "status": "已出账", "disbursed_at": now}
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"出账失败: {str(e)}"}
    finally:
        conn.close()


def repay_advance(advance_id: str, repayment_amount: float, repayment_date: str, remark: str = None) -> dict:
    """
    垫资还款
    
    Args:
        advance_id: 垫资单ID
        repayment_amount: 还款金额
        repayment_date: 还款日期
        remark: 备注
        
    Returns:
        还款结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        advance = cursor.fetchone()
        
        if not advance:
            return {"success": False, "message": "垫资单不存在"}
        
        advance_dict = row_to_dict(advance)
        current_status = advance_dict["status"]
        
        # 检查状态
        if current_status not in ["已出账", "逾期"]:
            return {"success": False, "message": f"当前状态【{current_status}】不可还款"}
        
        # 计算利息
        start_date = datetime.strptime(advance_dict["start_date"], "%Y-%m-%d")
        repay_date = datetime.strptime(repayment_date, "%Y-%m-%d")
        days = (repay_date - start_date).days
        
        advance_amount = Decimal(str(advance_dict["advance_amount"]))
        interest_rate = Decimal(str(advance_dict["interest_rate"]))
        interest_amount = advance_amount * interest_rate * days
        total_amount = advance_amount + interest_amount
        
        # 更新垫资单
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE advances
            SET status = '已还清', actual_repayment_date = ?, repayment_amount = ?,
                interest_amount = ?, total_amount = ?, updated_at = ?
            WHERE advance_id = ?
        """, (repayment_date, repayment_amount, float(interest_amount), float(total_amount), now, advance_id))
        
        conn.commit()
        
        result = {
            "advance_id": advance_id,
            "repayment_amount": repayment_amount,
            "interest_amount": float(interest_amount),
            "total_amount": float(total_amount),
            "actual_days": days,
            "status": "已还清"
        }
        
        return {
            "success": True,
            "message": "还款成功",
            "data": result
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"还款失败: {str(e)}"}
    finally:
        conn.close()


def calculate_interest(advance_id: str, repayment_date: str = None) -> dict:
    """
    计算垫资利息
    
    Args:
        advance_id: 垫资单ID
        repayment_date: 还款日期，默认为今天
        
    Returns:
        利息计算结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM advances WHERE advance_id = ?", (advance_id,))
        advance = cursor.fetchone()
        
        if not advance:
            return {"success": False, "message": "垫资单不存在"}
        
        advance_dict = row_to_dict(advance)
        
        # 计算天数
        start_date = datetime.strptime(advance_dict["start_date"], "%Y-%m-%d")
        if repayment_date:
            end_date = datetime.strptime(repayment_date, "%Y-%m-%d")
        else:
            end_date = datetime.now()
        
        days = (end_date - start_date).days
        
        # 计算利息
        advance_amount = Decimal(str(advance_dict["advance_amount"]))
        interest_rate = Decimal(str(advance_dict["interest_rate"]))
        interest_amount = advance_amount * interest_rate * days
        total_amount = advance_amount + interest_amount
        
        return {
            "success": True,
            "data": {
                "advance_amount": float(advance_amount),
                "interest_rate": float(interest_rate),
                "days": days,
                "interest_amount": float(interest_amount),
                "total_amount": float(total_amount)
            }
        }
    finally:
        conn.close()


def check_overdue() -> dict:
    """
    检测逾期垫资单
    
    Returns:
        逾期检测结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 查找逾期未还的垫资单
        cursor.execute("""
            SELECT advance_id, order_id, advance_amount, expected_repayment_date
            FROM advances
            WHERE status = '已出账' AND expected_repayment_date < ?
        """, (today,))
        
        overdue_list = cursor.fetchall()
        
        if not overdue_list:
            return {"success": True, "message": "无逾期垫资单", "data": {"overdue_count": 0}}
        
        # 批量更新为逾期状态
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        overdue_ids = [row["advance_id"] for row in overdue_list]
        
        for advance_id in overdue_ids:
            cursor.execute("""
                UPDATE advances SET status = '逾期', updated_at = ? WHERE advance_id = ?
            """, (now, advance_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"检测到{len(overdue_list)}笔逾期",
            "data": {
                "overdue_count": len(overdue_list),
                "overdue_advances": [row_to_dict(row) for row in overdue_list]
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"检测失败: {str(e)}"}
    finally:
        conn.close()


def get_advance_list(
    status: str = None,
    order_id: str = None,
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    获取垫资单列表
    
    Args:
        status: 状态筛选
        order_id: 订单ID筛选
        page: 页码
        page_size: 每页数量
        
    Returns:
        垫资单列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if order_id:
            conditions.append("order_id = ?")
            params.append(order_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM advances WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT a.*, o.customer_id, c.name as customer_name
            FROM advances a
            LEFT JOIN orders o ON a.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE {where_clause}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(list_sql, params + [page_size, offset])
        
        advances = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": advances
            }
        }
    finally:
        conn.close()


def get_advance_detail(advance_id: str) -> dict:
    """
    获取垫资单详情
    
    Args:
        advance_id: 垫资单ID
        
    Returns:
        垫资单详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.*, o.customer_id, c.name as customer_name, c.phone as customer_phone
            FROM advances a
            LEFT JOIN orders o ON a.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE a.advance_id = ?
        """, (advance_id,))
        
        advance = cursor.fetchone()
        
        if not advance:
            return {"success": False, "message": "垫资单不存在"}
        
        return {
            "success": True,
            "data": row_to_dict(advance)
        }
    finally:
        conn.close()


def get_dashboard() -> dict:
    """
    获取垫资仪表盘数据
    
    Returns:
        仪表盘数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        # 当前垫资余额（所有未还清垫资单的本金之和）
        cursor.execute("""
            SELECT COALESCE(SUM(advance_amount), 0) as balance
            FROM advances
            WHERE status IN ('已出账', '逾期')
        """)
        current_balance = cursor.fetchone()["balance"]
        
        # 今日新垫资
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(advance_amount), 0) as amount
            FROM advances
            WHERE DATE(created_at) = ?
        """, (today,))
        today_row = cursor.fetchone()
        
        # 本月新垫资
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(advance_amount), 0) as amount
            FROM advances
            WHERE DATE(created_at) >= ?
        """, (month_start,))
        month_row = cursor.fetchone()
        
        # 待还垫资笔数
        cursor.execute("""
            SELECT COUNT(*) as count FROM advances WHERE status = '已出账'
        """)
        pending_count = cursor.fetchone()["count"]
        
        # 逾期笔数
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(advance_amount), 0) as amount
            FROM advances WHERE status = '逾期'
        """)
        overdue_row = cursor.fetchone()
        
        # 近30天垫资余额趋势
        balance_trend = []
        for i in range(30, -1, -1):
            trend_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            
            # 计算该日期时的垫资余额（简化计算）
            cursor.execute("""
                SELECT COALESCE(SUM(advance_amount), 0) as balance
                FROM advances
                WHERE DATE(start_date) <= ?
                  AND (actual_repayment_date IS NULL OR DATE(actual_repayment_date) >= ?)
            """, (trend_date, trend_date))
            
            day_balance = cursor.fetchone()["balance"]
            balance_trend.append({"date": trend_date, "balance": day_balance})
        
        return {
            "success": True,
            "data": {
                "current_balance": current_balance,
                "today_new_count": today_row["count"],
                "today_new_amount": today_row["amount"],
                "month_new_count": month_row["count"],
                "month_new_amount": month_row["amount"],
                "pending_repay_count": pending_count,
                "overdue_count": overdue_row["count"],
                "overdue_amount": overdue_row["amount"],
                "balance_trend": balance_trend
            }
        }
    finally:
        conn.close()
