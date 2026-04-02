"""
FastAPI 应用入口
垫资管理模块 MVP 后端
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
import sqlite3
import random

from database import get_db_connection, DB_PATH
from models import (
    OrderCreate, OrderResponse,
    AdvanceCreate, AdvanceApproval, AdvanceDisburse, AdvanceRepay,
    AdvanceResponse, AdvanceListResponse,
    DashboardResponse, ApiResponse, PaginatedResponse,
    AdvanceStatus, LenderType, InterestRateType
)

# 创建 FastAPI 应用
app = FastAPI(
    title="汽车分期管理平台 - 垫资管理模块",
    description="垫资管理 MVP 后端 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 辅助函数 ====================

def generate_order_no() -> str:
    """生成订单号: DD-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"DD-{today}-{random_num}"


def generate_advance_no() -> str:
    """生成垫资单号: DZ-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"DZ-{today}-{random_num}"


def calculate_interest(amount: Decimal, daily_rate: Decimal, days: int) -> Decimal:
    """
    计算垫资利息
    公式：利息 = 垫资金额 × 日利率 × 实际天数
    """
    return amount * daily_rate * days


def get_remaining_days(expected_repay_date: date, current_date: date = None) -> Optional[int]:
    """计算剩余天数"""
    if current_date is None:
        current_date = date.today()
    
    delta = expected_repay_date - current_date
    return delta.days


def row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row)


# ==================== 订单管理 API ====================

@app.post("/api/v1/orders", response_model=ApiResponse, tags=["订单管理"])
async def create_order(order: OrderCreate):
    """创建测试订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        order_no = generate_order_no()
        
        cursor.execute("""
            INSERT INTO orders (order_no, customer_name, customer_phone, car_model, 
                              car_price, down_payment, loan_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, order.customer_name, order.customer_phone, order.car_model,
            order.car_price, order.down_payment, order.loan_amount, "pending"
        ))
        
        order_id = cursor.lastrowid
        conn.commit()
        
        # 查询创建的订单
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()
        
        return ApiResponse(
            code=200,
            message="订单创建成功",
            data={"order": row_to_dict(order_row)}
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/orders", response_model=PaginatedResponse, tags=["订单管理"])
async def list_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取订单列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询总数
        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        cursor.execute("""
            SELECT * FROM orders
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "orders": orders
            }
        }
    finally:
        conn.close()


# ==================== 垫资单管理 API ====================

@app.post("/api/v1/advances", response_model=ApiResponse, tags=["垫资管理"])
async def create_advance(advance: AdvanceCreate):
    """创建垫资单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证订单是否存在
        cursor.execute("SELECT id, customer_name FROM orders WHERE id = ?", (advance.order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 生成垫资单号
        advance_no = generate_advance_no()
        
        # 计算日利率
        daily_rate = advance.daily_rate
        if advance.interest_rate_type == InterestRateType.MONTHLY:
            daily_rate = advance.monthly_rate / 30
        
        # 插入垫资单
        cursor.execute("""
            INSERT INTO advances (
                advance_no, order_id, customer_name, amount,
                lender_type, lender_account, purpose,
                interest_rate_type, monthly_rate, daily_rate,
                start_date, expected_repay_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            advance_no, advance.order_id, advance.customer_name, advance.amount,
            advance.lender_type.value, advance.lender_account, advance.purpose,
            advance.interest_rate_type.value, advance.monthly_rate, daily_rate,
            advance.start_date, advance.expected_repay_date, 
            AdvanceStatus.PENDING_APPROVAL.value
        ))
        
        advance_id = cursor.lastrowid
        conn.commit()
        
        # 查询创建的垫资单
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        advance_row = cursor.fetchone()
        
        return ApiResponse(
            code=200,
            message="垫资单创建成功",
            data={"advance": row_to_dict(advance_row)}
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建垫资单失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/advances", response_model=PaginatedResponse, tags=["垫资管理"])
async def list_advances(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    start_date: Optional[date] = Query(None, description="开始日期筛选"),
    end_date: Optional[date] = Query(None, description="结束日期筛选")
):
    """获取垫资单列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if start_date:
            where_clauses.append("start_date >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("start_date <= ?")
            params.append(end_date)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM advances WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT id, advance_no, customer_name, amount, status,
                   calculated_interest, start_date, expected_repay_date
            FROM advances
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [page_size, offset])
        
        advances = []
        for row in cursor.fetchall():
            advance_dict = row_to_dict(row)
            # 计算剩余天数
            advance_dict["remaining_days"] = get_remaining_days(row["expected_repay_date"])
            advances.append(advance_dict)
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "advances": advances
            }
        }
    finally:
        conn.close()


@app.get("/api/v1/advances/{advance_id}", response_model=ApiResponse, tags=["垫资管理"])
async def get_advance_detail(advance_id: int):
    """获取垫资单详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="垫资单不存在")
        
        advance_dict = row_to_dict(row)
        advance_dict["remaining_days"] = get_remaining_days(row["expected_repay_date"])
        
        return ApiResponse(
            code=200,
            message="success",
            data={"advance": advance_dict}
        )
    finally:
        conn.close()


@app.post("/api/v1/advances/{advance_id}/approve", response_model=ApiResponse, tags=["垫资管理"])
async def approve_advance(advance_id: int, approval: AdvanceApproval):
    """垫资审批"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        advance_row = cursor.fetchone()
        
        if not advance_row:
            raise HTTPException(status_code=404, detail="垫资单不存在")
        
        # 检查状态
        if advance_row["status"] != AdvanceStatus.PENDING_APPROVAL.value:
            raise HTTPException(
                status_code=400,
                detail=f"垫资单状态为 {advance_row['status']}，无法审批"
            )
        
        # 更新状态
        new_status = AdvanceStatus.APPROVED.value if approval.approved else AdvanceStatus.REJECTED.value
        current_time = datetime.now()
        
        cursor.execute("""
            UPDATE advances
            SET status = ?, approver = ?, approval_opinion = ?, 
                approval_time = ?, updated_at = ?
            WHERE id = ?
        """, (
            new_status, approval.approver, approval.approval_opinion,
            current_time, current_time, advance_id
        ))
        
        conn.commit()
        
        # 查询更新后的数据
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        updated_row = cursor.fetchone()
        
        return ApiResponse(
            code=200,
            message=f"审批{'通过' if approval.approved else '拒绝'}",
            data={"advance": row_to_dict(updated_row)}
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"审批失败: {str(e)}")
    finally:
        conn.close()


@app.post("/api/v1/advances/{advance_id}/disburse", response_model=ApiResponse, tags=["垫资管理"])
async def disburse_advance(advance_id: int, disburse: AdvanceDisburse):
    """垫资出账"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        advance_row = cursor.fetchone()
        
        if not advance_row:
            raise HTTPException(status_code=404, detail="垫资单不存在")
        
        # 检查状态
        if advance_row["status"] != AdvanceStatus.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail=f"垫资单状态为 {advance_row['status']}，无法出账"
            )
        
        # 更新状态
        current_time = disburse.disburse_time or datetime.now()
        
        cursor.execute("""
            UPDATE advances
            SET status = ?, disburse_time = ?, updated_at = ?
            WHERE id = ?
        """, (
            AdvanceStatus.DISBURSED.value, current_time, current_time, advance_id
        ))
        
        conn.commit()
        
        # 查询更新后的数据
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        updated_row = cursor.fetchone()
        
        return ApiResponse(
            code=200,
            message="出账成功",
            data={"advance": row_to_dict(updated_row)}
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"出账失败: {str(e)}")
    finally:
        conn.close()


@app.post("/api/v1/advances/{advance_id}/repay", response_model=ApiResponse, tags=["垫资管理"])
async def repay_advance(advance_id: int, repay: AdvanceRepay):
    """垫资还款"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询垫资单
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        advance_row = cursor.fetchone()
        
        if not advance_row:
            raise HTTPException(status_code=404, detail="垫资单不存在")
        
        # 检查状态
        if advance_row["status"] not in [AdvanceStatus.DISBURSED.value, AdvanceStatus.OVERDUE.value]:
            raise HTTPException(
                status_code=400,
                detail=f"垫资单状态为 {advance_row['status']}，无法还款"
            )
        
        # 计算实际利息
        amount = Decimal(str(advance_row["amount"]))
        daily_rate = Decimal(str(advance_row["daily_rate"]))
        start_date = datetime.strptime(advance_row["start_date"], "%Y-%m-%d").date()
        repay_time = repay.repay_time or datetime.now()
        
        # 计算实际天数
        actual_days = (repay_time.date() - start_date).days
        
        # 计算利息
        calculated_interest = calculate_interest(amount, daily_rate, actual_days)
        
        # 更新状态
        cursor.execute("""
            UPDATE advances
            SET status = ?, actual_repay_amount = ?, calculated_interest = ?,
                actual_repay_date = ?, repay_time = ?, updated_at = ?
            WHERE id = ?
        """, (
            AdvanceStatus.REPAID.value, repay.actual_repay_amount, calculated_interest,
            repay_time.date(), repay_time, repay_time, advance_id
        ))
        
        conn.commit()
        
        # 查询更新后的数据
        cursor.execute("SELECT * FROM advances WHERE id = ?", (advance_id,))
        updated_row = cursor.fetchone()
        
        result = row_to_dict(updated_row)
        result["actual_days"] = actual_days
        result["calculated_interest"] = float(calculated_interest)
        
        return ApiResponse(
            code=200,
            message="还款成功",
            data={"advance": result}
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"还款失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/advances/dashboard", response_model=ApiResponse, tags=["垫资管理"])
async def get_dashboard():
    """垫资仪表盘"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = date.today()
        month_start = today.replace(day=1)
        
        # 当前垫资余额（所有未还清垫资单的本金之和）
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as balance
            FROM advances
            WHERE status IN ('disbursed', 'overdue')
        """)
        current_balance = Decimal(str(cursor.fetchone()["balance"]))
        
        # 今日新垫资
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as amount
            FROM advances
            WHERE DATE(created_at) = ?
        """, (today,))
        today_row = cursor.fetchone()
        today_new_advances = today_row["count"]
        today_new_amount = Decimal(str(today_row["amount"]))
        
        # 本月新垫资
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as amount
            FROM advances
            WHERE DATE(created_at) >= ?
        """, (month_start,))
        month_row = cursor.fetchone()
        month_new_advances = month_row["count"]
        month_new_amount = Decimal(str(month_row["amount"]))
        
        # 待还垫资笔数
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM advances
            WHERE status = 'disbursed'
        """)
        pending_repay_count = cursor.fetchone()["count"]
        
        # 逾期笔数
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM advances
            WHERE status = 'overdue'
        """)
        overdue_count = cursor.fetchone()["count"]
        
        # 近30天垫资余额趋势
        balance_trend = []
        for i in range(30, -1, -1):
            trend_date = today - timedelta(days=i)
            
            # 计算该日期时的垫资余额
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as balance
                FROM advances
                WHERE start_date <= ?
                  AND (actual_repay_date IS NULL OR actual_repay_date >= ?)
            """, (trend_date, trend_date))
            
            day_balance = Decimal(str(cursor.fetchone()["balance"]))
            
            balance_trend.append({
                "date": trend_date.isoformat(),
                "balance": float(day_balance)
            })
        
        dashboard_data = {
            "current_balance": float(current_balance),
            "today_new_advances": today_new_advances,
            "today_new_amount": float(today_new_amount),
            "month_new_advances": month_new_advances,
            "month_new_amount": float(month_new_amount),
            "pending_repay_count": pending_repay_count,
            "overdue_count": overdue_count,
            "balance_trend": balance_trend
        }
        
        return ApiResponse(
            code=200,
            message="success",
            data=dashboard_data
        )
    finally:
        conn.close()


# ==================== 定时任务：逾期检测 ====================

@app.post("/api/v1/advances/check-overdue", response_model=ApiResponse, tags=["系统维护"])
async def check_overdue():
    """
    检测逾期垫资单
    找出所有已过预计还款日但未还清的垫资单，自动标记为逾期
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = date.today()
        
        # 查找逾期未还的垫资单
        cursor.execute("""
            SELECT id, advance_no, customer_name, amount, expected_repay_date
            FROM advances
            WHERE status = 'disbursed'
              AND expected_repay_date < ?
        """, (today,))
        
        overdue_advances = cursor.fetchall()
        
        if not overdue_advances:
            return ApiResponse(
                code=200,
                message="没有逾期垫资单",
                data={"overdue_count": 0}
            )
        
        # 批量更新为逾期状态
        overdue_ids = [row["id"] for row in overdue_advances]
        placeholders = ",".join("?" * len(overdue_ids))
        
        cursor.execute(f"""
            UPDATE advances
            SET status = 'overdue', updated_at = ?
            WHERE id IN ({placeholders})
        """, [datetime.now()] + overdue_ids)
        
        conn.commit()
        
        return ApiResponse(
            code=200,
            message=f"已标记 {len(overdue_advances)} 笔垫资单为逾期",
            data={
                "overdue_count": len(overdue_advances),
                "overdue_advances": [
                    {
                        "id": row["id"],
                        "advance_no": row["advance_no"],
                        "customer_name": row["customer_name"],
                        "amount": float(row["amount"]),
                        "expected_repay_date": row["expected_repay_date"]
                    }
                    for row in overdue_advances
                ]
            }
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"逾期检测失败: {str(e)}")
    finally:
        conn.close()


# ==================== 根路由 ====================

@app.get("/", tags=["系统信息"])
async def root():
    """根路由"""
    return {
        "message": "汽车分期管理平台 - 垫资管理模块 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["系统信息"])
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动垫资管理模块 API 服务...")
    print("📖 API 文档: http://localhost:8000/docs")
    print("📖 ReDoc 文档: http://localhost:8000/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8000)
