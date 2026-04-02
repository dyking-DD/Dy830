"""
GPS管理模块 API路由
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from gps_service import (
    GPSService, GPSAlertService, GPSDashboardService, GPSPollService,
    DeviceCreate, HeartbeatRequest, AlertCreate, AlertHandle,
    ApiResponse
)

# 创建路由器
router = APIRouter(prefix="/api/v1/gps", tags=["GPS管理"])


# ==================== 辅助函数 ====================

def success_response(data: dict = None, message: str = "success") -> dict:
    """统一成功响应"""
    return {
        "code": 200,
        "message": message,
        "data": data or {}
    }


def error_response(message: str, code: int = 400) -> dict:
    """统一错误响应"""
    return {
        "code": code,
        "message": message,
        "data": None
    }


# ==================== GPS设备管理 API ====================

@router.post("/devices", summary="注册GPS设备")
async def register_device(device: DeviceCreate):
    """
    注册GPS设备
    
    - **order_id**: 关联订单ID
    - **imei**: 设备IMEI号（15-20位）
    - **device_type**: 设备类型（wired/wireless/hidden）
    - **install_location**: 安装位置
    - **install_staff**: 安装人员
    
    设备录入后关联订单状态自动变为"GPS安装中"
    """
    try:
        result = GPSService.create_device(device)
        return success_response({"device": result}, "GPS设备注册成功")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.get("/devices", summary="获取设备列表")
async def list_devices(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选：在线/离线/告警中")
):
    """
    获取GPS设备列表
    
    - 支持按状态筛选（在线/离线/告警中）
    - 支持分页
    - 返回设备基本信息和关联客户名
    """
    try:
        result = GPSService.list_devices(page, page_size, status)
        return success_response(result)
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.get("/devices/{device_id}", summary="获取设备详情")
async def get_device_detail(device_id: str):
    """
    获取GPS设备详情
    
    - 设备基本信息
    - 关联订单信息
    - 当前状态
    """
    try:
        result = GPSService.get_device_detail(device_id)
        return success_response({"device": result})
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.get("/devices/{device_id}/location", summary="获取设备最新位置")
async def get_device_location(device_id: str):
    """
    获取GPS设备最新位置
    
    - 返回当前经纬度
    - 如果没有位置数据，返回模拟位置
    """
    try:
        result = GPSService.get_device_location(device_id)
        return success_response({"location": result})
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


# ==================== GPS心跳与状态 API ====================

@router.post("/devices/{device_id}/heartbeat", summary="设备心跳")
async def device_heartbeat(device_id: str, heartbeat: HeartbeatRequest):
    """
    设备心跳上报
    
    - 接收当前GPS位置
    - 自动更新在线状态为"在线"
    - 更新最后心跳时间
    - 如果超过5分钟无心跳，系统自动标记为"离线"
    """
    try:
        result = GPSService.device_heartbeat(device_id, heartbeat)
        return success_response(result, "心跳更新成功")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.post("/devices/{device_id}/offline", summary="标记设备离线")
async def mark_device_offline(device_id: str):
    """
    手动标记设备离线
    
    - 用于测试或特殊情况
    """
    try:
        result = GPSService.mark_device_offline(device_id)
        return success_response(result, "设备已标记为离线")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.post("/check-offline", summary="检查离线设备")
async def check_offline_devices():
    """
    检查超过5分钟无心跳的设备
    
    - 自动标记为离线
    - 建议定时任务调用
    """
    try:
        count = GPSService.check_offline_devices()
        return success_response({"marked_count": count}, f"已标记 {count} 台设备为离线")
    except Exception as e:
        return error_response(str(e), 500)


# ==================== GPS告警管理 API ====================

@router.post("/alerts", summary="添加告警")
async def create_alert(alert: AlertCreate):
    """
    添加GPS告警
    
    - **device_id**: 设备ID
    - **alert_type**: 告警类型
        - overspeed: 超速告警
        - out_of_zone: 出区域告警
        - power_off: 断电告警
        - tamper: 拆机告警
        - low_battery: 低电量告警
        - sos: SOS报警
    - **location**: 告警位置（可选）
    - **alert_time**: 告警时间（默认当前时间）
    
    设备状态自动变为"告警中"
    """
    try:
        result = GPSAlertService.create_alert(alert)
        return success_response({"alert": result}, "告警创建成功")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.get("/alerts", summary="获取告警列表")
async def list_alerts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    handled: Optional[bool] = Query(None, description="处理状态筛选：true已处理/false未处理"),
    alert_type: Optional[str] = Query(None, description="告警类型筛选")
):
    """
    获取GPS告警列表
    
    - 支持按处理状态筛选
    - 支持按告警类型筛选
    - 支持分页
    """
    try:
        result = GPSAlertService.list_alerts(page, page_size, handled, alert_type)
        return success_response(result)
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


@router.post("/alerts/{alert_id}/handle", summary="处理告警")
async def handle_alert(alert_id: str, handle: AlertHandle):
    """
    处理GPS告警
    
    - **handled_by**: 处理人
    - **handle_note**: 处理备注（可选）
    
    处理后设备状态恢复"在线"（如果无其他未处理告警）
    """
    try:
        result = GPSAlertService.handle_alert(alert_id, handle)
        return success_response({"alert": result}, "告警处理成功")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


# ==================== GPS驾驶舱 API ====================

@router.get("/dashboard", summary="GPS监控驾驶舱")
async def get_dashboard():
    """
    获取GPS监控驾驶舱数据
    
    返回：
    - **total_devices**: 设备总数
    - **online_count**: 在线数
    - **offline_count**: 离线数
    - **alert_count**: 告警数
    - **today_installed**: 今日安装数
    - **pending_install**: 待安装数（已提车但未安装GPS的订单数）
    - **recent_alerts**: 最近10条未处理告警
    """
    try:
        result = GPSDashboardService.get_dashboard()
        return success_response(result)
    except HTTPException as e:
        return error_response(e.detail, e.status_code)


# ==================== GPS轮询模拟 API ====================

@router.get("/poll", summary="模拟轮询设备")
async def poll_devices():
    """
    模拟轮询所有GPS设备
    
    - 遍历所有设备，随机模拟状态变化
    - 模拟产生1-2个告警
    - 返回轮询结果统计
    
    用于测试和演示
    """
    try:
        result = GPSPollService.poll_devices()
        return success_response(result, f"轮询完成，检查 {result['checked']} 台设备")
    except HTTPException as e:
        return error_response(e.detail, e.status_code)
