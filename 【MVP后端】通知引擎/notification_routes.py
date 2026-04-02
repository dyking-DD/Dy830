# -*- coding: utf-8 -*-
"""
通知引擎路由层
定义所有API端点
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import models
from notification_service import NotificationService


# 创建路由器
router = APIRouter(prefix="/api/v1/notifications", tags=["通知引擎"])

# 创建服务实例
service = NotificationService()


# ==================== 通知模板管理 ====================

@router.get("/templates", summary="获取所有通知模板")
async def get_all_templates():
    """
    获取所有通知模板列表
    
    返回内置的所有通知模板，包括模板编码、名称、内容模板、适用渠道等。
    """
    try:
        templates = service.get_all_templates()
        return models.ApiResponse(
            code=200,
            message="获取模板列表成功",
            data=templates
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"获取模板列表失败: {str(e)}",
            data=None
        )


@router.get("/templates/{template_code}", summary="获取单个模板详情")
async def get_template_detail(template_code: str):
    """
    根据模板编码获取模板详情
    
    - **template_code**: 模板编码，如 order_created、advance_approved 等
    """
    try:
        template = service.get_template_by_code(template_code)
        
        if not template:
            return models.ApiResponse(
                code=404,
                message=f"未找到模板: {template_code}",
                data=None
            )
        
        return models.ApiResponse(
            code=200,
            message="获取模板详情成功",
            data=template
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"获取模板详情失败: {str(e)}",
            data=None
        )


# ==================== 发送通知 ====================

@router.post("/send", summary="发送通知")
async def send_notification(request: models.NotificationSendRequest):
    """
    发送单条通知
    
    - **order_id**: 订单ID（可选）
    - **channel**: 通知渠道（wechat/sms/app_push/system）
    - **recipient**: 接收人姓名
    - **recipient_phone**: 接收人手机号
    - **template_code**: 模板编码（可选）
    - **template_params**: 模板参数（可选）
    - **content**: 完整通知内容（可选，如果不提供则根据模板生成）
    
    返回发送结果，包括日志ID、状态和消息。
    """
    try:
        result = service.send_notification(request)
        return models.ApiResponse(
            code=200,
            message="发送通知成功",
            data=result.model_dump()
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"发送通知失败: {str(e)}",
            data=None
        )


# ==================== 批量发送 ====================

@router.post("/batch", summary="批量发送通知")
async def batch_send_notifications(request: models.NotificationBatchRequest):
    """
    批量发送通知
    
    接收通知列表数组，逐条发送并返回统计结果。
    
    - **notifications**: 通知列表数组
    
    返回发送统计，包括总数、成功数、失败数和每条发送结果。
    """
    try:
        result = service.batch_send(request)
        return models.ApiResponse(
            code=200,
            message="批量发送完成",
            data=result.model_dump()
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"批量发送失败: {str(e)}",
            data=None
        )


# ==================== 业务节点触发通知 ====================

@router.post("/trigger", summary="业务节点触发通知")
async def trigger_notification(request: models.NotificationTriggerRequest):
    """
    根据业务阶段自动触发通知（核心功能）
    
    根据传入的stage（业务阶段）自动匹配对应的通知模板并发送。
    
    支持的业务阶段：
    - order_created: 接单成功
    - advance_approved: 垫资审批通过
    - advance_disbursed: 垫资已出账
    - bank_approved: 银行审批通过
    - loan_notified: 放款通知
    - car_picked: 已提车
    - gps_online: GPS已在线
    - archive_complete: 资料归档完成
    - mortgage_complete: 抵押完成
    - repayment_reminder: 还款提醒
    - overdue_3d: 逾期3天
    - overdue_7d: 逾期7天
    - settled: 已结清
    
    - **stage**: 业务阶段编码
    - **order_id**: 订单ID
    - **recipient**: 接收人姓名
    - **recipient_phone**: 接收人手机号
    - **channel**: 通知渠道（默认system）
    - **template_params**: 模板参数（根据不同模板需要不同参数）
    
    返回发送结果。
    """
    try:
        result = service.trigger_notification(request)
        return models.ApiResponse(
            code=200,
            message="触发通知成功",
            data=result.model_dump()
        )
    except ValueError as e:
        return models.ApiResponse(
            code=400,
            message=str(e),
            data=None
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"触发通知失败: {str(e)}",
            data=None
        )


# ==================== 通知日志 ====================

@router.get("/logs", summary="查询通知日志")
async def get_notification_logs(
    order_id: Optional[str] = Query(None, description="订单ID筛选"),
    channel: Optional[str] = Query(None, description="渠道筛选"),
    status: Optional[str] = Query(None, description="状态筛选（已发送/发送失败/待发送）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询通知日志列表
    
    支持多条件筛选和分页：
    - **order_id**: 按订单ID筛选
    - **channel**: 按渠道筛选（wechat/sms/app_push/system）
    - **status**: 按状态筛选（已发送/发送失败/待发送）
    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    
    返回日志列表和分页信息。
    """
    try:
        result = service.get_logs(
            order_id=order_id,
            channel=channel,
            status=status,
            page=page,
            page_size=page_size
        )
        return models.ApiResponse(
            code=200,
            message="查询日志成功",
            data=result
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"查询日志失败: {str(e)}",
            data=None
        )


@router.get("/logs/{log_id}", summary="获取日志详情")
async def get_log_detail(log_id: str):
    """
    根据日志ID获取日志详情
    
    - **log_id**: 日志ID
    
    返回完整的日志信息，包括通知内容、状态、发送时间等。
    """
    try:
        log = service.get_log_by_id(log_id)
        
        if not log:
            return models.ApiResponse(
                code=404,
                message=f"未找到日志: {log_id}",
                data=None
            )
        
        return models.ApiResponse(
            code=200,
            message="获取日志详情成功",
            data=log.model_dump()
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"获取日志详情失败: {str(e)}",
            data=None
        )


# ==================== 通知统计 ====================

@router.get("/stats", summary="获取通知统计")
async def get_notification_stats():
    """
    获取通知发送统计数据
    
    返回以下统计信息：
    - **today_sent**: 今日发送数
    - **week_sent**: 本周发送数
    - **month_sent**: 本月发送数
    - **by_channel**: 各渠道发送量统计
    - **success_rate**: 发送成功率
    """
    try:
        stats = service.get_statistics()
        return models.ApiResponse(
            code=200,
            message="获取统计数据成功",
            data=stats.model_dump()
        )
    except Exception as e:
        return models.ApiResponse(
            code=500,
            message=f"获取统计数据失败: {str(e)}",
            data=None
        )
