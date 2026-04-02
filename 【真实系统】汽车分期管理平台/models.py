# -*- coding: utf-8 -*-
"""
统一数据模型
汽车分期管理平台 - 所有模块的Pydantic模型
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ==================== 用户角色枚举 ====================

class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"        # 超级管理员
    FINANCE = "finance"    # 财务
    OPERATIONS = "operation"  # 运营/贷后
    COLLECTIONS = "collections"  # 贷后催收
    BOSS = "boss"          # 老板
    CUSTOMER = "customer"  # 客户


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = 200
    message: str = "success"
    data: Any = None


class PaginatedResponse(BaseModel):
    """分页响应"""
    code: int = 200
    message: str = "success"
    data: Dict[str, Any] = None


# ==================== 客户模型 ====================

class CustomerCreate(BaseModel):
    """创建客户请求"""
    name: str = Field(..., description="客户姓名")
    phone: str = Field(..., description="客户电话")
    id_number: Optional[str] = Field(None, description="身份证号")
    address: Optional[str] = Field(None, description="地址")


class CustomerResponse(BaseModel):
    """客户响应"""
    customer_id: str
    name: str
    phone: str
    id_number: Optional[str]
    address: Optional[str]
    created_at: Optional[str]


# ==================== 订单模型 ====================

class OrderCreate(BaseModel):
    """创建订单请求"""
    customer_name: str = Field(..., description="客户姓名")
    customer_phone: str = Field(..., description="客户电话")
    customer_id_number: Optional[str] = Field(None, description="客户身份证号")
    customer_address: Optional[str] = Field(None, description="客户地址")
    car_brand: str = Field(..., description="车辆品牌")
    car_model: str = Field(..., description="车辆型号")
    car_vin: Optional[str] = Field(None, description="车架号")
    car_plate_number: Optional[str] = Field(None, description="车牌号")
    car_price: float = Field(..., description="车辆价格")
    loan_amount: float = Field(..., description="贷款金额")
    down_payment: float = Field(..., description="首付金额")
    loan_period: int = Field(..., description="贷款期限（月）")
    monthly_payment: float = Field(..., description="月供金额")
    interest_rate: Optional[float] = Field(None, description="利率")
    bank_name: Optional[str] = Field(None, description="贷款银行")
    created_by: str = Field(..., description="创建人")


class OrderStageUpdate(BaseModel):
    """更新订单阶段请求"""
    new_stage: str = Field(..., description="新阶段")
    remark: Optional[str] = Field(None, description="备注")


class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, description="车牌号")
    vin: Optional[str] = Field(None, description="车架号")
    remark: Optional[str] = Field(None, description="备注（可存base64图片）")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str
    customer_id: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    stage: str
    stage_remark: Optional[str]
    loan_amount: float
    down_payment: float
    loan_period: int
    monthly_payment: float
    interest_rate: Optional[float]
    bank_name: Optional[str]
    created_by: str
    created_at: Optional[str]
    stage_updated_at: Optional[str]


# ==================== 垫资模型 ====================

class AdvanceCreate(BaseModel):
    """创建垫资单请求"""
    order_id: str = Field(..., description="订单ID")
    advance_amount: float = Field(..., description="垫资金额")
    payer_type: str = Field(..., description="出资方类型")
    payer_account: Optional[str] = Field(None, description="出资方账户")
    purpose: Optional[str] = Field(None, description="垫资用途")
    interest_rate: float = Field(..., description="日利率")
    start_date: str = Field(..., description="开始日期")
    expected_repayment_date: str = Field(..., description="预计还款日期")
    created_by: str = Field(..., description="创建人")


class AdvanceApprove(BaseModel):
    """审批垫资单请求"""
    approver: str = Field(..., description="审批人")
    opinion: str = Field(..., description="审批意见")
    approved: bool = Field(..., description="是否通过")


class AdvanceDisburse(BaseModel):
    """垫资出账请求"""
    disburse_by: str = Field(..., description="出账人")


class AdvanceRepay(BaseModel):
    """垫资还款请求"""
    repayment_amount: float = Field(..., description="还款金额")
    repayment_date: str = Field(..., description="还款日期")
    remark: Optional[str] = Field(None, description="备注")


class AdvanceResponse(BaseModel):
    """垫资单响应"""
    advance_id: str
    order_id: str
    advance_amount: float
    status: str
    interest_rate: Optional[float]
    start_date: Optional[str]
    expected_repayment_date: Optional[str]
    interest_amount: Optional[float]
    total_amount: Optional[float]
    created_at: Optional[str]


# ==================== GPS模型 ====================

class DeviceType(str, Enum):
    """设备类型"""
    WIRED = "有线"
    WIRELESS = "无线"
    HIDDEN = "隐蔽"


class GPSDeviceCreate(BaseModel):
    """注册GPS设备请求"""
    order_id: str = Field(..., description="关联订单ID")
    imei: str = Field(..., description="设备IMEI号")
    device_type: str = Field(..., description="设备类型")
    install_location: str = Field(..., description="安装位置")
    install_staff: str = Field(..., description="安装人员")


class GPSHeartbeat(BaseModel):
    """设备心跳请求"""
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    location: Optional[str] = Field(None, description="地址")


class GPSAlertCreate(BaseModel):
    """创建GPS告警请求"""
    device_id: str = Field(..., description="设备ID")
    alert_type: str = Field(..., description="告警类型")
    location: Optional[str] = Field(None, description="告警位置")


class GPSAlertHandle(BaseModel):
    """处理告警请求"""
    handled_by: str = Field(..., description="处理人")
    handle_note: Optional[str] = Field(None, description="处理备注")


class GPSDeviceResponse(BaseModel):
    """GPS设备响应"""
    device_id: str
    order_id: str
    imei: str
    device_type: str
    install_location: str
    install_staff: str
    online_status: str
    last_heartbeat: Optional[str]
    current_location: Optional[str]


class GPSAlertResponse(BaseModel):
    """GPS告警响应"""
    alert_id: str
    device_id: str
    alert_type: str
    alert_time: str
    location: Optional[str]
    handled: bool
    handled_by: Optional[str]
    handled_time: Optional[str]


class GPSDashboard(BaseModel):
    """GPS驾驶舱"""
    total_devices: int
    online_count: int
    offline_count: int
    alert_count: int
    today_installed: int
    pending_install: int
    recent_alerts: List[dict]


# ==================== 归档模型 ====================

class ArchiveUpload(BaseModel):
    """上传归档资料请求"""
    order_id: str = Field(..., description="订单ID")
    document_type: str = Field(..., description="资料类型")
    file_name: str = Field(..., description="文件名")
    file_url: str = Field(..., description="文件URL")
    uploaded_by: str = Field(..., description="上传人")


class ArchiveChecklistResponse(BaseModel):
    """归档清单响应"""
    checklist_id: str
    order_id: str
    id_card_front: int
    id_card_back: int
    driving_license: int
    vehicle_certificate: int
    gps_photos: int
    pickup_confirmation: int
    advance_agreement: int
    invoice: int
    insurance: int
    overall_status: str


class ArchiveStatusResponse(BaseModel):
    """归档状态响应"""
    order_id: str
    overall_status: str
    progress_percent: float
    items: List[dict]


class ArchiveStats(BaseModel):
    """归档统计"""
    total_orders: int
    complete_count: int
    partial_count: int
    pending_count: int
    complete_rate: float
    missing_documents: List[dict]


# ==================== 还款模型 ====================

class RepaymentPlanGenerate(BaseModel):
    """生成还款计划请求"""
    order_id: str = Field(..., description="订单ID")
    loan_amount: float = Field(..., description="贷款金额")
    loan_period: int = Field(..., description="贷款期限（月）")
    start_date: str = Field(..., description="开始日期")
    monthly_payment: float = Field(..., description="月供金额")


class RepaymentRecordCreate(BaseModel):
    """录入还款记录请求"""
    plan_id: str = Field(..., description="还款计划ID")
    order_id: str = Field(..., description="订单ID")
    actual_amount: float = Field(..., description="实际还款金额")
    repayment_date: str = Field(..., description="还款日期")
    payment_method: Optional[str] = Field(None, description="还款方式")
    remark: Optional[str] = Field(None, description="备注")


class RepaymentPlanResponse(BaseModel):
    """还款计划响应"""
    plan_id: str
    order_id: str
    period_number: int
    due_date: str
    due_amount: float
    actual_date: Optional[str]
    actual_amount: Optional[float]
    status: str


class RepaymentDashboard(BaseModel):
    """还款驾驶舱"""
    today_repayment: float
    month_repayment: float
    today_actual: float
    overdue_count: int
    overdue_amount: float
    normal_count: int


# ==================== 抵押模型 ====================

class MortgageCreate(BaseModel):
    """创建抵押登记请求"""
    order_id: str = Field(..., description="订单ID")
    mortgage_bank: str = Field(..., description="抵押银行")
    register_date: str = Field(..., description="登记日期")
    expire_date: Optional[str] = Field(None, description="到期日期")
    certificate_number: Optional[str] = Field(None, description="登记证编号")


class MortgageRelease(BaseModel):
    """解押请求"""
    release_date: str = Field(..., description="解押日期")


class MortgageResponse(BaseModel):
    """抵押响应"""
    mortgage_id: str
    order_id: str
    mortgage_bank: str
    register_date: Optional[str]
    expire_date: Optional[str]
    certificate_number: Optional[str]
    status: str
    release_date: Optional[str]


class MortgageStats(BaseModel):
    """抵押统计"""
    total: int
    mortgaged_count: int
    released_count: int
    expire_soon_count: int


# ==================== 通知模型 ====================

class NotificationSend(BaseModel):
    """发送通知请求"""
    order_id: Optional[str] = Field(None, description="订单ID")
    channel: str = Field(..., description="通知渠道")
    recipient: str = Field(..., description="收件人")
    recipient_phone: str = Field(..., description="收件人电话")
    template_code: Optional[str] = Field(None, description="模板编码")
    template_params: Optional[Dict[str, str]] = Field(None, description="模板参数")
    content: Optional[str] = Field(None, description="通知内容")


class NotificationTrigger(BaseModel):
    """触发通知请求"""
    order_id: str = Field(..., description="订单ID")
    stage: str = Field(..., description="业务阶段")
    channel: str = Field(default="system", description="通知渠道")
    recipient: str = Field(..., description="收件人")
    recipient_phone: str = Field(..., description="收件人电话")
    template_params: Optional[Dict[str, str]] = Field(None, description="模板参数")


class NotificationLog(BaseModel):
    """通知日志"""
    log_id: str
    order_id: Optional[str]
    channel: str
    recipient: str
    recipient_phone: str
    template_code: Optional[str]
    content: str
    status: str
    sent_at: Optional[str]
    error_message: Optional[str]
    created_at: str


class NotificationStats(BaseModel):
    """通知统计"""
    today_sent: int
    week_sent: int
    month_sent: int
    by_channel: Dict[str, int]
    success_rate: float


# ==================== 资料类型配置 ====================

DOCUMENT_TYPE_CONFIG = {
    "id_card_front": {"name": "身份证人像面", "required": True},
    "id_card_back": {"name": "身份证国徽面", "required": True},
    "driving_license": {"name": "行驶证", "required": True},
    "vehicle_certificate": {"name": "车辆登记证", "required": True},
    "gps_photos": {"name": "GPS安装照片", "required": True},
    "pickup_confirmation": {"name": "提车确认单", "required": True},
    "advance_agreement": {"name": "垫资协议", "required": True},
    "invoice": {"name": "购车发票", "required": False},
    "insurance": {"name": "保险单", "required": False},
}

REQUIRED_DOCUMENTS = [k for k, v in DOCUMENT_TYPE_CONFIG.items() if v["required"]]


# ==================== 全局驾驶舱模型 ====================

class GlobalDashboard(BaseModel):
    """全局驾驶舱"""
    orders_stats: Dict[str, Any]
    advances_stats: Dict[str, Any]
    gps_stats: Dict[str, Any]
    archive_stats: Dict[str, Any]
    repayment_stats: Dict[str, Any]
    mortgage_stats: Dict[str, Any]


# ==================== 认证相关模型 ====================

class LoginRequest(BaseModel):
    """管理员登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class CustomerLoginRequest(BaseModel):
    """客户登录请求"""
    phone: str = Field(..., description="手机号")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    user_id: str
    name: str
    role: str
    customer_id: Optional[str] = None  # 前台客户才有


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    name: str
    role: str
    username: Optional[str] = None
    customer_id: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None


class AdminUserCreate(BaseModel):
    """创建管理员用户请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(default="123456", description="密码")
    name: str = Field(..., description="姓名")
    role: str = Field(..., description="角色")
    department: Optional[str] = Field(None, description="部门")


class CustomerAccountCreate(BaseModel):
    """创建客户账户请求"""
    customer_id: str = Field(..., description="客户ID")
    phone: str = Field(..., description="手机号")
    password: str = Field(default="123456", description="密码")
