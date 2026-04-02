# -*- coding: utf-8 -*-
"""
通知服务模块
处理通知发送、日志记录等业务逻辑
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, generate_id


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


# ==================== 内置通知模板库 ====================

NOTIFICATION_TEMPLATES = {
    "order_created": {
        "template_code": "order_created",
        "name": "接单通知",
        "content_template": "您已提交分期申请，单号{order_id}，我们将在24小时内联系您。",
        "channel": "system",
        "remark": "客户提交分期申请后触发"
    },
    "advance_approved": {
        "template_code": "advance_approved",
        "name": "垫资审批通过",
        "content_template": "您的垫资申请已通过，金额{amount}元，预计{date}到账。",
        "channel": "system",
        "remark": "垫资审批通过后触发"
    },
    "advance_disbursed": {
        "template_code": "advance_disbursed",
        "name": "垫资已出账",
        "content_template": "垫资{amount}元已出账，请知悉。",
        "channel": "system",
        "remark": "垫资出账后触发"
    },
    "bank_approved": {
        "template_code": "bank_approved",
        "name": "银行审批通过",
        "content_template": "恭喜！您的分期申请已通过审核，可安排提车。",
        "channel": "system",
        "remark": "银行审批通过后触发"
    },
    "loan_notified": {
        "template_code": "loan_notified",
        "name": "放款通知提车",
        "content_template": "银行已放款，请前往{dealer}提车，联系人：{contact}。",
        "channel": "system",
        "remark": "银行放款后触发"
    },
    "car_picked": {
        "template_code": "car_picked",
        "name": "已提车",
        "content_template": "您已成功提车，感谢选择我们的服务！",
        "channel": "system",
        "remark": "客户提车后触发"
    },
    "gps_online": {
        "template_code": "gps_online",
        "name": "GPS已在线",
        "content_template": "您的车辆GPS已在线，设备IMEI：{imei}，如有问题请联系客服。",
        "channel": "system",
        "remark": "GPS设备上线后触发"
    },
    "archive_complete": {
        "template_code": "archive_complete",
        "name": "归档完成",
        "content_template": "您的资料已归档完成，本月还款{amount}元，请按时还款。",
        "channel": "system",
        "remark": "资料归档完成后触发"
    },
    "mortgage_complete": {
        "template_code": "mortgage_complete",
        "name": "抵押完成",
        "content_template": "您的车辆抵押手续已完成。",
        "channel": "system",
        "remark": "抵押完成后触发"
    },
    "repayment_reminder": {
        "template_code": "repayment_reminder",
        "name": "还款提醒",
        "content_template": "您好，本月还款金额{amount}元，请于{date}日前存入还款账户。",
        "channel": "system",
        "remark": "还款日前触发"
    },
    "overdue_3d": {
        "template_code": "overdue_3d",
        "name": "逾期3天提醒",
        "content_template": "您有一笔分期已逾期3天，请尽快处理，以免影响信用。",
        "channel": "system",
        "remark": "逾期3天后触发"
    },
    "overdue_7d": {
        "template_code": "overdue_7d",
        "name": "逾期7天警告",
        "content_template": "严重提醒：您的分期已逾期7天，请立即处理，否则将采取法律措施。",
        "channel": "system",
        "remark": "逾期7天后触发"
    },
    "settled": {
        "template_code": "settled",
        "name": "结清通知",
        "content_template": "恭喜！您的分期已全部还清，请携带身份证前往办理解押。",
        "channel": "system",
        "remark": "分期结清后触发"
    }
}

# 业务阶段与模板映射
STAGE_TEMPLATE_MAPPING = {
    "已接单": "order_created",
    "垫资已出账": "advance_disbursed",
    "银行审批通过": "bank_approved",
    "放款通知": "loan_notified",
    "已提车": "car_picked",
    "GPS已在线": "gps_online",
    "归档完成": "archive_complete",
    "已抵押": "mortgage_complete",
    "已结清": "settled"
}


def get_all_templates() -> List[Dict]:
    """获取所有通知模板"""
    return list(NOTIFICATION_TEMPLATES.values())


def get_template_by_code(template_code: str) -> Optional[Dict]:
    """根据模板编码获取模板详情"""
    return NOTIFICATION_TEMPLATES.get(template_code)


def render_template(template: str, params: Dict[str, str]) -> str:
    """渲染模板内容"""
    content = template
    for key, value in params.items():
        content = content.replace(f"{{{key}}}", str(value))
    return content


def generate_log_id() -> str:
    """生成日志ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:8]
    return f"LOG{timestamp}{random_str}"


def send_notification(data: dict) -> dict:
    """
    发送通知
    
    Args:
        data: 包含订单ID、渠道、收件人、模板编码等信息
        
    Returns:
        发送结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取通知内容
        content = data.get("content")
        template_code = data.get("template_code")
        template_params = data.get("template_params", {})
        
        if not content and template_code:
            template = get_template_by_code(template_code)
            if template:
                content = render_template(template["content_template"], template_params)
        
        if not content:
            content = "通知内容"
        
        # 模拟发送（实际项目中应调用真实的第三方API）
        send_result = _mock_send(data.get("channel"), data.get("recipient_phone"), content)
        
        # 生成日志ID
        log_id = generate_log_id()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 记录日志
        status = "已发送" if send_result["success"] else "发送失败"
        sent_at = now if send_result["success"] else None
        error_message = send_result.get("error") if not send_result["success"] else None
        
        cursor.execute("""
            INSERT INTO notification_logs (
                log_id, order_id, channel, recipient, recipient_phone,
                template_code, content, status, sent_at, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, data.get("order_id"), data.get("channel"),
            data.get("recipient"), data.get("recipient_phone"),
            template_code, content, status, sent_at, error_message, now
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "通知发送成功" if send_result["success"] else "通知发送失败",
            "data": {
                "log_id": log_id,
                "status": status,
                "sent_at": sent_at
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"发送失败: {str(e)}"}
    finally:
        conn.close()


def trigger_notification(order_id: str, stage: str, channel: str, recipient: str, recipient_phone: str, template_params: dict = None) -> dict:
    """
    根据业务阶段触发通知
    
    Args:
        order_id: 订单ID
        stage: 业务阶段
        channel: 通知渠道
        recipient: 收件人
        recipient_phone: 收件人电话
        template_params: 模板参数
        
    Returns:
        触发结果
    """
    # 获取对应的模板编码
    template_code = STAGE_TEMPLATE_MAPPING.get(stage)
    if not template_code:
        return {"success": False, "message": f"阶段【{stage}】无对应通知模板"}
    
    # 构建发送请求
    send_data = {
        "order_id": order_id,
        "channel": channel,
        "recipient": recipient,
        "recipient_phone": recipient_phone,
        "template_code": template_code,
        "template_params": template_params or {}
    }
    
    return send_notification(send_data)


def get_logs(order_id: str = None, channel: str = None, status: str = None, page: int = 1, page_size: int = 20) -> dict:
    """查询通知日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if order_id:
            conditions.append("order_id = ?")
            params.append(order_id)
        
        if channel:
            conditions.append("channel = ?")
            params.append(channel)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM notification_logs WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT * FROM notification_logs 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [page_size, offset])
        
        logs = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": logs
            }
        }
    finally:
        conn.close()


def get_stats() -> dict:
    """获取通知统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 今日发送数
        cursor.execute(
            "SELECT COUNT(*) as count FROM notification_logs WHERE created_at >= ?",
            (today_start.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        today_sent = cursor.fetchone()["count"]
        
        # 本周发送数
        cursor.execute(
            "SELECT COUNT(*) as count FROM notification_logs WHERE created_at >= ?",
            (week_start.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        week_sent = cursor.fetchone()["count"]
        
        # 本月发送数
        cursor.execute(
            "SELECT COUNT(*) as count FROM notification_logs WHERE created_at >= ?",
            (month_start.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        month_sent = cursor.fetchone()["count"]
        
        # 各渠道发送量
        cursor.execute(
            "SELECT channel, COUNT(*) as count FROM notification_logs GROUP BY channel"
        )
        by_channel = {row["channel"]: row["count"] for row in cursor.fetchall()}
        
        # 发送成功率
        cursor.execute("SELECT COUNT(*) as total FROM notification_logs")
        total_count = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as success FROM notification_logs WHERE status = '已发送'")
        success_count = cursor.fetchone()["success"]
        
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0
        
        return {
            "success": True,
            "data": {
                "today_sent": today_sent,
                "week_sent": week_sent,
                "month_sent": month_sent,
                "by_channel": by_channel,
                "success_rate": round(success_rate, 2)
            }
        }
    finally:
        conn.close()


def _mock_send(channel: str, phone: str, content: str) -> dict:
    """
    模拟发送通知
    实际项目中应该调用真实的第三方API
    """
    # 打印日志（模拟发送过程）
    print(f"\n{'='*60}")
    print(f"📤 模拟发送通知")
    print(f"渠道: {channel}")
    print(f"手机: {phone}")
    print(f"内容: {content}")
    print(f"{'='*60}\n")
    
    # 模拟95%成功率
    import random
    success_rate = 0.95
    
    if random.random() < success_rate:
        return {"success": True, "message": f"通过{channel}渠道发送成功"}
    else:
        return {"success": False, "message": "发送失败", "error": "模拟发送失败（测试用）"}
