# -*- coding: utf-8 -*-
"""
通知引擎数据模型
使用 Pydantic 进行数据验证
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 请求模型 ====================

class NotificationSendRequest(BaseModel):
    """发送通知请求"""
    order_id: Optional[str] = Field(None, description="订单ID（可选）")
    channel: str = Field(..., description="通知渠道：wechat/sms/app_push/system")
    recipient: str = Field(..., description="接收人姓名")
    recipient_phone: str = Field(..., description="接收人手机")
    template_code: Optional[str] = Field(None, description="模板编码")
    template_params: Optional[Dict[str, str]] = Field(None, description="模板参数")
    content: Optional[str] = Field(None, description="通知内容（完整内容）")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD202401010001",
                "channel": "wechat",
                "recipient": "张三",
                "recipient_phone": "13800138000",
                "template_code": "order_created",
                "template_params": {"order_id": "ORD202401010001"},
                "content": "您已提交分期申请，单号ORD202401010001，我们将在24小时内联系您。"
            }
        }


class NotificationBatchRequest(BaseModel):
    """批量发送通知请求"""
    notifications: List[NotificationSendRequest] = Field(..., description="通知列表")

    class Config:
        json_schema_extra = {
            "example": {
                "notifications": [
                    {
                        "order_id": "ORD202401010001",
                        "channel": "wechat",
                        "recipient": "张三",
                        "recipient_phone": "13800138000",
                        "template_code": "order_created",
                        "template_params": {"order_id": "ORD202401010001"}
                    }
                ]
            }
        }


class NotificationTriggerRequest(BaseModel):
    """业务节点触发通知请求"""
    stage: str = Field(..., description="业务阶段编码")
    order_id: str = Field(..., description="订单ID")
    recipient: str = Field(..., description="接收人姓名")
    recipient_phone: str = Field(..., description="接收人手机")
    channel: str = Field(default="system", description="通知渠道：wechat/sms/app_push/system")
    template_params: Optional[Dict[str, str]] = Field(None, description="模板参数")

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "order_created",
                "order_id": "ORD202401010001",
                "recipient": "张三",
                "recipient_phone": "13800138000",
                "channel": "wechat",
                "template_params": {"order_id": "ORD202401010001"}
            }
        }


# ==================== 响应模型 ====================

class NotificationTemplate(BaseModel):
    """通知模板"""
    template_code: str
    name: str
    content_template: str
    channel: str
    remark: Optional[str] = None


class NotificationLog(BaseModel):
    """通知日志"""
    log_id: str
    order_id: Optional[str] = None
    channel: str
    recipient: str
    recipient_phone: str
    template_code: Optional[str] = None
    content: str
    status: str
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


class NotificationSendResponse(BaseModel):
    """发送通知响应"""
    log_id: str
    status: str
    message: str


class NotificationBatchResponse(BaseModel):
    """批量发送响应"""
    total: int
    success_count: int
    failed_count: int
    results: List[NotificationSendResponse]


class NotificationStats(BaseModel):
    """通知统计"""
    today_sent: int
    week_sent: int
    month_sent: int
    by_channel: Dict[str, int]
    success_rate: float


# ==================== 统一响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[any] = Field(None, description="响应数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "操作成功",
                "data": {}
            }
        }
