# -*- coding: utf-8 -*-
"""
通知引擎服务层
处理通知发送、日志记录等核心业务逻辑
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from database import get_db_connection, init_database
import models


# ==================== 内置通知模板库 ====================
# 模板数据（hardcoded，不存储在数据库中）

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


# ==================== 业务阶段与模板映射 ====================

STAGE_TEMPLATE_MAPPING = {
    "order_created": "order_created",
    "advance_approved": "advance_approved",
    "advance_disbursed": "advance_disbursed",
    "bank_approved": "bank_approved",
    "loan_notified": "loan_notified",
    "car_picked": "car_picked",
    "gps_online": "gps_online",
    "archive_complete": "archive_complete",
    "mortgage_complete": "mortgage_complete",
    "repayment_reminder": "repayment_reminder",
    "overdue_3d": "overdue_3d",
    "overdue_7d": "overdue_7d",
    "settled": "settled"
}


class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        """初始化服务"""
        init_database()
    
    # ==================== 模板管理 ====================
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """获取所有通知模板"""
        return list(NOTIFICATION_TEMPLATES.values())
    
    def get_template_by_code(self, template_code: str) -> Optional[Dict[str, Any]]:
        """根据模板编码获取模板详情"""
        return NOTIFICATION_TEMPLATES.get(template_code)
    
    # ==================== 发送通知 ====================
    
    def send_notification(self, request: models.NotificationSendRequest) -> models.NotificationSendResponse:
        """
        发送通知（模拟发送）
        实际不调用第三方API，只记录日志
        """
        # 生成日志ID
        log_id = self._generate_log_id()
        
        # 获取通知内容
        content = request.content
        if not content and request.template_code:
            # 如果没有提供完整内容，则根据模板和参数生成
            template = self.get_template_by_code(request.template_code)
            if template:
                content = self._render_template(
                    template["content_template"],
                    request.template_params or {}
                )
        
        if not content:
            content = "通知内容"  # 默认内容
        
        # 模拟发送（这里可以添加实际的发送逻辑）
        send_result = self._mock_send(request.channel, request.recipient_phone, content)
        
        # 记录日志
        status = "已发送" if send_result["success"] else "发送失败"
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if send_result["success"] else None
        error_message = send_result.get("error") if not send_result["success"] else None
        
        self._save_log(
            log_id=log_id,
            order_id=request.order_id,
            channel=request.channel,
            recipient=request.recipient,
            recipient_phone=request.recipient_phone,
            template_code=request.template_code,
            content=content,
            status=status,
            sent_at=sent_at,
            error_message=error_message
        )
        
        return models.NotificationSendResponse(
            log_id=log_id,
            status=status,
            message=send_result["message"]
        )
    
    # ==================== 批量发送 ====================
    
    def batch_send(self, request: models.NotificationBatchRequest) -> models.NotificationBatchResponse:
        """批量发送通知"""
        results = []
        success_count = 0
        failed_count = 0
        
        for notification in request.notifications:
            result = self.send_notification(notification)
            results.append(result)
            
            if result.status == "已发送":
                success_count += 1
            else:
                failed_count += 1
        
        return models.NotificationBatchResponse(
            total=len(request.notifications),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
    
    # ==================== 业务节点触发通知 ====================
    
    def trigger_notification(self, request: models.NotificationTriggerRequest) -> models.NotificationSendResponse:
        """
        根据业务阶段触发通知
        自动匹配对应的模板并发送
        """
        # 验证业务阶段
        if request.stage not in STAGE_TEMPLATE_MAPPING:
            raise ValueError(f"不支持的业务阶段: {request.stage}")
        
        # 获取对应的模板编码
        template_code = STAGE_TEMPLATE_MAPPING[request.stage]
        
        # 获取模板
        template = self.get_template_by_code(template_code)
        if not template:
            raise ValueError(f"未找到模板: {template_code}")
        
        # 渲染模板内容
        content = self._render_template(
            template["content_template"],
            request.template_params or {}
        )
        
        # 构建发送请求
        send_request = models.NotificationSendRequest(
            order_id=request.order_id,
            channel=request.channel,
            recipient=request.recipient,
            recipient_phone=request.recipient_phone,
            template_code=template_code,
            template_params=request.template_params,
            content=content
        )
        
        # 发送通知
        return self.send_notification(send_request)
    
    # ==================== 日志查询 ====================
    
    def get_logs(
        self,
        order_id: Optional[str] = None,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """查询通知日志（支持筛选和分页）"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        rows = cursor.fetchall()
        
        conn.close()
        
        # 转换为模型列表
        logs = [self._row_to_log(row) for row in rows]
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "logs": logs
        }
    
    def get_log_by_id(self, log_id: str) -> Optional[models.NotificationLog]:
        """根据日志ID获取日志详情"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM notification_logs WHERE log_id = ?",
            (log_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_log(row)
    
    # ==================== 统计分析 ====================
    
    def get_statistics(self) -> models.NotificationStats:
        """获取通知统计数据"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        cursor.execute(
            "SELECT COUNT(*) as success FROM notification_logs WHERE status = '已发送'"
        )
        success_count = cursor.fetchone()["success"]
        
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0
        
        conn.close()
        
        return models.NotificationStats(
            today_sent=today_sent,
            week_sent=week_sent,
            month_sent=month_sent,
            by_channel=by_channel,
            success_rate=round(success_rate, 2)
        )
    
    # ==================== 私有方法 ====================
    
    def _generate_log_id(self) -> str:
        """生成日志ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:8]
        return f"LOG{timestamp}{random_str}"
    
    def _render_template(self, template: str, params: Dict[str, str]) -> str:
        """渲染模板内容"""
        content = template
        for key, value in params.items():
            content = content.replace(f"{{{key}}}", str(value))
        return content
    
    def _mock_send(self, channel: str, phone: str, content: str) -> Dict[str, Any]:
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

        # ── 真实渠道发送（取消注释即可启用）─────────────────────────
        if channel == "dingtalk":
            try:
                from dingtalk import send_order_notification
                result = send_order_notification(
                    webhook_url="https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
                    secret="YOUR_SECRET",
                    order_id="",
                    customer_name=phone,
                    stage=channel,
                    remark=content
                )
                return result
            except Exception as e:
                return {"success": False, "message": f"钉钉发送失败: {e}"}
        elif channel == "sms":
            # TODO: 接入阿里云/腾讯云短信
            # from sms import send_sms; return send_sms(phone, content)
            pass
        elif channel == "wecom":
            # TODO: 接入企业微信机器人
            pass
        # ──────────────────────────────────────────────────────────

        # 默认模拟发送
        import random
        success_rate = 0.95  # 95%成功率

        if random.random() < success_rate:
            return {
                "success": True,
                "message": f"通过{channel}渠道发送成功"
            }
        else:
            return {
                "success": False,
                "message": "发送失败",
                "error": "模拟发送失败（测试用）"
            }
    
    def _save_log(
        self,
        log_id: str,
        order_id: Optional[str],
        channel: str,
        recipient: str,
        recipient_phone: str,
        template_code: Optional[str],
        content: str,
        status: str,
        sent_at: Optional[str],
        error_message: Optional[str]
    ):
        """保存通知日志"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notification_logs 
            (log_id, order_id, channel, recipient, recipient_phone, template_code, 
             content, status, sent_at, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_id,
            order_id,
            channel,
            recipient,
            recipient_phone,
            template_code,
            content,
            status,
            sent_at,
            error_message,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        conn.commit()
        conn.close()
    
    def _row_to_log(self, row) -> models.NotificationLog:
        """将数据库行转换为日志模型"""
        return models.NotificationLog(
            log_id=row["log_id"],
            order_id=row["order_id"],
            channel=row["channel"],
            recipient=row["recipient"],
            recipient_phone=row["recipient_phone"],
            template_code=row["template_code"],
            content=row["content"],
            status=row["status"],
            sent_at=row["sent_at"],
            error_message=row["error_message"],
            created_at=row["created_at"]
        )
