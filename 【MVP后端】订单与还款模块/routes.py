"""
API路由定义
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from models import (
    OrderCreate, OrderStageUpdate,
    RepaymentPlanGenerate, RepaymentRecordCreate,
    MortgageCreate, MortgageRelease,
    ApiResponse
)
from service import OrderService, RepaymentService, MortgageService, DashboardService

# 创建路由器
router = APIRouter()

# ==================== 订单管理路由 ====================

@router.post("/orders", summary="创建订单")
async def create_order(order: OrderCreate):
    """创建新订单"""
    try:
        result = OrderService.create_order(order.dict())
        return ApiResponse(code=200, message="订单创建成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"创建订单失败: {str(e)}")

@router.get("/orders", summary="订单列表")
async def get_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    stage: Optional[str] = Query(None, description="订单阶段筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    date_start: Optional[str] = Query(None, description="开始日期"),
    date_end: Optional[str] = Query(None, description="结束日期")
):
    """获取订单列表（支持分页、筛选、搜索）"""
    try:
        result = OrderService.get_orders_list(
            page=page,
            page_size=page_size,
            stage=stage,
            keyword=keyword,
            date_start=date_start,
            date_end=date_end
        )
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询订单列表失败: {str(e)}")

@router.get("/orders/{order_id}", summary="订单详情")
async def get_order_detail(order_id: str):
    """获取订单完整详情"""
    try:
        result = OrderService.get_order_detail(order_id)
        if not result:
            return ApiResponse(code=404, message="订单不存在")
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询订单详情失败: {str(e)}")

@router.put("/orders/{order_id}/stage", summary="更新订单阶段")
async def update_order_stage(order_id: str, stage_update: OrderStageUpdate):
    """更新订单阶段（严格状态机检查）"""
    try:
        result = OrderService.update_order_stage(
            order_id=order_id,
            new_stage=stage_update.stage,
            remark=stage_update.remark
        )
        if not result.get("success"):
            return ApiResponse(code=400, message=result.get("message"))
        return ApiResponse(code=200, message="订单阶段更新成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"更新订单阶段失败: {str(e)}")

# ==================== 还款管理路由 ====================

@router.post("/repayments/plans/generate", summary="生成还款计划")
async def generate_repayment_plans(plan: RepaymentPlanGenerate):
    """为订单生成还款计划"""
    try:
        result = RepaymentService.generate_repayment_plans(
            order_id=plan.order_id,
            loan_amount=plan.loan_amount,
            loan_period=plan.loan_period,
            start_date=plan.start_date,
            monthly_payment=plan.monthly_payment
        )
        if not result.get("success"):
            return ApiResponse(code=400, message=result.get("message"))
        return ApiResponse(code=200, message="还款计划生成成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"生成还款计划失败: {str(e)}")

@router.get("/repayments/plans", summary="还款计划列表")
async def get_repayment_plans(
    order_id: Optional[str] = Query(None, description="订单ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取还款计划列表"""
    try:
        result = RepaymentService.get_repayment_plans(
            order_id=order_id,
            status=status,
            page=page,
            page_size=page_size
        )
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询还款计划失败: {str(e)}")

@router.get("/repayments/plans/{plan_id}", summary="还款计划详情")
async def get_repayment_plan_detail(plan_id: str):
    """获取还款计划详情"""
    try:
        result = RepaymentService.get_repayment_plan_detail(plan_id)
        if not result:
            return ApiResponse(code=404, message="还款计划不存在")
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询还款计划详情失败: {str(e)}")

@router.post("/repayments/records", summary="录入还款记录")
async def create_repayment_record(record: RepaymentRecordCreate):
    """录入还款记录"""
    try:
        result = RepaymentService.create_repayment_record(record.dict())
        if not result.get("success"):
            return ApiResponse(code=400, message=result.get("message"))
        return ApiResponse(code=200, message="还款记录录入成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"录入还款记录失败: {str(e)}")

@router.get("/repayments/records", summary="还款记录列表")
async def get_repayment_records(
    order_id: Optional[str] = Query(None, description="订单ID筛选"),
    date_start: Optional[str] = Query(None, description="开始日期"),
    date_end: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取还款记录列表"""
    try:
        result = RepaymentService.get_repayment_records(
            order_id=order_id,
            date_start=date_start,
            date_end=date_end,
            page=page,
            page_size=page_size
        )
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询还款记录失败: {str(e)}")

@router.get("/repayments/check-overdue", summary="检测逾期")
async def check_overdue():
    """检测逾期还款计划并自动更新状态"""
    try:
        result = RepaymentService.check_overdue()
        return ApiResponse(code=200, message="逾期检测完成", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"逾期检测失败: {str(e)}")

@router.get("/repayments/stats", summary="还款统计")
async def get_repayment_stats():
    """获取还款统计数据"""
    try:
        result = RepaymentService.get_repayment_stats()
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询还款统计失败: {str(e)}")

# ==================== 抵押管理路由 ====================

@router.post("/mortgage", summary="创建抵押登记")
async def create_mortgage(mortgage: MortgageCreate):
    """创建抵押登记"""
    try:
        result = MortgageService.create_mortgage(mortgage.dict())
        return ApiResponse(code=200, message="抵押登记创建成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"创建抵押登记失败: {str(e)}")

@router.get("/mortgage", summary="抵押列表")
async def get_mortgages(
    order_id: Optional[str] = Query(None, description="订单ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选")
):
    """获取抵押列表"""
    try:
        result = MortgageService.get_mortgages(
            order_id=order_id,
            status=status
        )
        return ApiResponse(code=200, message="查询成功", data={"items": result})
    except Exception as e:
        return ApiResponse(code=500, message=f"查询抵押列表失败: {str(e)}")

@router.get("/mortgage/{order_id}", summary="抵押详情")
async def get_mortgage_detail(order_id: str):
    """根据订单ID获取抵押详情"""
    try:
        result = MortgageService.get_mortgage_by_order(order_id)
        if not result:
            return ApiResponse(code=404, message="抵押记录不存在")
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询抵押详情失败: {str(e)}")

@router.post("/mortgage/{order_id}/release", summary="解除抵押")
async def release_mortgage(order_id: str, release_data: MortgageRelease):
    """解除抵押"""
    try:
        result = MortgageService.release_mortgage(
            order_id=order_id,
            release_date=release_data.release_date
        )
        if not result.get("success"):
            return ApiResponse(code=400, message=result.get("message"))
        return ApiResponse(code=200, message="抵押解除成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"解除抵押失败: {str(e)}")

@router.get("/mortgage/stats", summary="抵押统计")
async def get_mortgage_stats():
    """获取抵押统计数据"""
    try:
        result = MortgageService.get_mortgage_stats()
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询抵押统计失败: {str(e)}")

# ==================== 驾驶舱路由 ====================

@router.get("/dashboard", summary="全局驾驶舱")
async def get_dashboard():
    """获取全局驾驶舱数据"""
    try:
        result = DashboardService.get_dashboard()
        return ApiResponse(code=200, message="查询成功", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"查询驾驶舱数据失败: {str(e)}")
