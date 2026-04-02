"""
Pydantic模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# ==================== 订单相关模型 ====================

class OrderListResponse(BaseModel):
    """订单列表响应模型"""
    order_id: str
    customer_name: str
    customer_phone: str
    car_brand: str
    car_model: str
    loan_amount: float
    stage: str
    created_at: str

class OrderDetailResponse(BaseModel):
    """订单详情响应模型"""
    # 客户信息
    customer_name: str
    customer_phone: str
    customer_id_number: Optional[str] = None
    # 车辆信息
    car_brand: str
    car_model: str
    car_vin: Optional[str] = None
    car_plate_number: Optional[str] = None
    car_price: Optional[float] = None
    # 贷款信息
    loan_amount: float
    down_payment: float
    loan_period: int
    monthly_payment: float
    interest_rate: Optional[float] = None
    # 垫资信息
    advance_id: Optional[str] = None
    advance_amount: Optional[float] = None
    advance_status: Optional[str] = None
    # GPS信息
    gps_device_id: Optional[str] = None
    gps_imei: Optional[str] = None
    gps_online_status: Optional[str] = None
    # 归档信息
    archive_status: Optional[str] = None
    archive_progress_percent: int = 0
    # 阶段信息
    stage: str
    stage_remark: Optional[str] = None
    created_at: str
    stage_updated_at: Optional[str] = None

class OrderCreate(BaseModel):
    """创建订单请求模型"""
    customer_name: str = Field(..., description="客户姓名")
    customer_phone: str = Field(..., description="客户电话")
    customer_id_number: Optional[str] = Field(None, description="身份证号")
    car_brand: str = Field(..., description="车辆品牌")
    car_model: str = Field(..., description="车辆型号")
    car_vin: Optional[str] = Field(None, description="车架号")
    car_plate_number: Optional[str] = Field(None, description="车牌号")
    car_price: Optional[float] = Field(None, description="车辆价格")
    loan_amount: float = Field(..., description="贷款金额")
    down_payment: float = Field(..., description="首付金额")
    loan_period: int = Field(..., description="贷款期数")
    monthly_payment: float = Field(..., description="月供金额")
    interest_rate: Optional[float] = Field(None, description="利率")
    bank_name: Optional[str] = Field(None, description="贷款银行")
    created_by: str = Field(..., description="创建人")

class OrderStageUpdate(BaseModel):
    """订单阶段更新请求模型"""
    stage: str = Field(..., description="新阶段")
    remark: Optional[str] = Field(None, description="阶段备注")

# ==================== 还款计划相关模型 ====================

class RepaymentPlanGenerate(BaseModel):
    """还款计划生成请求模型"""
    order_id: str = Field(..., description="订单ID")
    loan_amount: float = Field(..., description="贷款金额")
    loan_period: int = Field(..., description="期数")
    start_date: str = Field(..., description="起始还款日")
    monthly_payment: float = Field(..., description="月供金额")

class RepaymentPlanResponse(BaseModel):
    """还款计划响应模型"""
    plan_id: str
    order_id: str
    customer_name: str
    period_number: int
    due_date: str
    due_amount: float
    actual_date: Optional[str] = None
    actual_amount: Optional[float] = None
    status: str
    overdue_days: int = 0

class RepaymentRecordCreate(BaseModel):
    """还款记录创建请求模型"""
    plan_id: str = Field(..., description="还款计划ID")
    actual_amount: float = Field(..., description="实还金额")
    repayment_date: str = Field(..., description="实还日期")
    payment_method: str = Field(..., description="支付方式")
    remark: Optional[str] = Field(None, description="备注")

class RepaymentRecordResponse(BaseModel):
    """还款记录响应模型"""
    record_id: str
    plan_id: str
    order_id: str
    actual_amount: float
    repayment_date: str
    payment_method: str
    remark: Optional[str] = None
    created_at: str

class RepaymentStatsResponse(BaseModel):
    """还款统计响应模型"""
    today_repayment: float = 0
    month_repayment: float = 0
    today_actual: float = 0
    overdue_count: int = 0
    overdue_amount: float = 0
    overdue_3d_count: int = 0
    overdue_7d_count: int = 0
    normal_count: int = 0

# ==================== 抵押相关模型 ====================

class MortgageCreate(BaseModel):
    """抵押登记创建请求模型"""
    order_id: str = Field(..., description="订单ID")
    mortgage_bank: str = Field(..., description="抵押银行")
    register_date: str = Field(..., description="登记日期")
    expire_date: str = Field(..., description="到期日期")
    certificate_number: Optional[str] = Field(None, description="登记证编号")

class MortgageResponse(BaseModel):
    """抵押信息响应模型"""
    mortgage_id: str
    order_id: str
    mortgage_bank: str
    register_date: str
    expire_date: str
    certificate_number: Optional[str] = None
    status: str
    release_date: Optional[str] = None
    created_at: str

class MortgageRelease(BaseModel):
    """解押请求模型"""
    release_date: str = Field(..., description="解押日期")

class MortgageStatsResponse(BaseModel):
    """抵押统计响应模型"""
    total: int = 0
    mortgaged_count: int = 0
    released_count: int = 0
    expire_soon_count: int = 0

# ==================== 驾驶舱相关模型 ====================

class DashboardResponse(BaseModel):
    """驾驶舱响应模型"""
    orders_stats: dict
    advances_stats: dict
    gps_stats: dict
    archive_stats: dict
    repayment_stats: dict
    mortgage_stats: dict

# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    total: int
    page: int
    page_size: int
    items: List[dict]
