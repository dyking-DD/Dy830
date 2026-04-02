"""
Pydantic 数据模型定义
包含请求和响应模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ==================== 枚举类型 ====================

class LenderType(str, Enum):
    """垫资方类型"""
    COMPANY = "company"
    PERSONAL = "personal"


class InterestRateType(str, Enum):
    """利率类型"""
    MONTHLY = "monthly"  # 月息
    DAILY = "daily"      # 日息


class AdvanceStatus(str, Enum):
    """垫资单状态"""
    PENDING_APPROVAL = "pending_approval"  # 待审批
    APPROVED = "approved"                  # 审批通过
    REJECTED = "rejected"                  # 审批拒绝
    DISBURSED = "disbursed"                # 已出账
    REPAID = "repaid"                      # 已还清
    OVERDUE = "overdue"                    # 逾期


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==================== 订单模型 ====================

class OrderCreate(BaseModel):
    """创建订单请求"""
    customer_name: str = Field(..., description="客户姓名")
    customer_phone: Optional[str] = Field(None, description="客户电话")
    car_model: Optional[str] = Field(None, description="车型")
    car_price: Optional[Decimal] = Field(None, description="车辆价格")
    down_payment: Optional[Decimal] = Field(None, description="首付金额")
    loan_amount: Optional[Decimal] = Field(None, description="贷款金额")


class OrderResponse(BaseModel):
    """订单响应"""
    id: int
    order_no: str
    customer_name: str
    customer_phone: Optional[str]
    car_model: Optional[str]
    car_price: Optional[Decimal]
    down_payment: Optional[Decimal]
    loan_amount: Optional[Decimal]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 垫资单模型 ====================

class AdvanceCreate(BaseModel):
    """创建垫资单请求"""
    order_id: int = Field(..., description="关联订单ID")
    customer_name: str = Field(..., description="客户姓名")
    amount: Decimal = Field(..., gt=0, description="垫资金额")
    lender_type: LenderType = Field(..., description="垫资方类型")
    lender_account: str = Field(..., description="垫资账户")
    purpose: Optional[str] = Field(None, description="垫资用途")
    interest_rate_type: InterestRateType = Field(default=InterestRateType.MONTHLY, description="利率类型")
    monthly_rate: Optional[Decimal] = Field(default=Decimal("0.015"), description="月利率，默认1.5%")
    daily_rate: Optional[Decimal] = Field(None, description="日利率")
    start_date: date = Field(..., description="垫资开始日期")
    expected_repay_date: date = Field(..., description="预计还款日期")
    
    @validator('expected_repay_date')
    def validate_repay_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('预计还款日期必须晚于开始日期')
        return v
    
    @validator('daily_rate')
    def validate_daily_rate(cls, v, values):
        # 如果选择日息但未提供日利率，自动计算（月利率/30）
        if values.get('interest_rate_type') == InterestRateType.DAILY:
            if v is None:
                monthly_rate = values.get('monthly_rate', Decimal("0.015"))
                return monthly_rate / 30
        return v


class AdvanceApproval(BaseModel):
    """垫资审批请求"""
    approver: str = Field(..., description="审批人")
    approval_opinion: str = Field(..., description="审批意见")
    approved: bool = Field(..., description="是否通过")


class AdvanceDisburse(BaseModel):
    """垫资出账请求"""
    disburse_time: Optional[datetime] = Field(None, description="实际出账时间，默认为当前时间")


class AdvanceRepay(BaseModel):
    """垫资还款请求"""
    actual_repay_amount: Decimal = Field(..., gt=0, description="实际还款金额")
    repay_time: Optional[datetime] = Field(None, description="实际还款时间，默认为当前时间")


class AdvanceResponse(BaseModel):
    """垫资单响应"""
    id: int
    advance_no: str
    order_id: int
    customer_name: str
    amount: Decimal
    lender_type: str
    lender_account: str
    purpose: Optional[str]
    interest_rate_type: str
    monthly_rate: Optional[Decimal]
    daily_rate: Optional[Decimal]
    start_date: date
    expected_repay_date: date
    actual_repay_date: Optional[date]
    actual_repay_amount: Optional[Decimal]
    calculated_interest: Optional[Decimal]
    status: str
    approver: Optional[str]
    approval_opinion: Optional[str]
    approval_time: Optional[datetime]
    disburse_time: Optional[datetime]
    repay_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # 计算字段
    remaining_days: Optional[int] = None  # 剩余天数

    class Config:
        from_attributes = True


class AdvanceListResponse(BaseModel):
    """垫资单列表响应"""
    id: int
    advance_no: str
    customer_name: str
    amount: Decimal
    status: str
    calculated_interest: Optional[Decimal]
    remaining_days: Optional[int]
    start_date: date
    expected_repay_date: date


# ==================== 仪表盘模型 ====================

class DashboardResponse(BaseModel):
    """垫资仪表盘响应"""
    current_balance: Decimal = Field(..., description="当前垫资余额")
    today_new_advances: int = Field(..., description="今日新垫资笔数")
    today_new_amount: Decimal = Field(..., description="今日新垫资金额")
    month_new_advances: int = Field(..., description="本月新垫资笔数")
    month_new_amount: Decimal = Field(..., description="本月新垫资金额")
    pending_repay_count: int = Field(..., description="待还垫资笔数")
    overdue_count: int = Field(..., description="逾期笔数")
    balance_trend: List[dict] = Field(..., description="近30天垫资余额趋势")


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[dict] = Field(None, description="数据")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel):
    """分页响应"""
    code: int = 200
    message: str = "success"
    data: dict = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
