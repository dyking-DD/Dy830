"""
FastAPI 应用入口
GPS管理模块 MVP 后端
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional

from gps_routes import router as gps_router
from gps_service import get_db_connection, init_database

# 创建 FastAPI 应用
app = FastAPI(
    title="汽车分期管理平台 - GPS管理模块",
    description="""
## GPS管理模块 MVP 后端 API

### 功能模块
- **GPS设备管理**: 设备注册、查询、状态管理
- **GPS心跳监控**: 设备心跳上报、在线状态监控
- **GPS告警管理**: 告警创建、查询、处理
- **GPS驾驶舱**: 监控数据汇总
- **GPS轮询模拟**: 模拟设备状态变化

### 技术栈
- Python 3 + FastAPI
- SQLite 数据库
- Pydantic 数据验证
    """,
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

# 注册路由
app.include_router(gps_router)


# ==================== 订单管理 API（简化版，用于测试） ====================

@app.post("/api/v1/orders", tags=["订单管理"])
async def create_test_order(
    customer_name: str,
    customer_phone: Optional[str] = None,
    car_model: Optional[str] = None,
    pickup_date: Optional[str] = None
):
    """
    创建测试订单（用于GPS设备关联）
    
    - customer_name: 客户姓名
    - customer_phone: 客户电话
    - car_model: 车型
    - pickup_date: 提车日期（YYYY-MM-DD）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 生成订单号
        import random
        order_no = f"DD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        current_time = datetime.now()
        
        # 插入订单
        cursor.execute("""
            INSERT INTO orders (order_no, customer_name, customer_phone, car_model, pickup_date, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (order_no, customer_name, customer_phone, car_model, pickup_date, current_time, current_time))
        
        order_id = cursor.lastrowid
        conn.commit()
        
        # 查询创建的订单
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = dict(cursor.fetchone())
        
        return {
            "code": 200,
            "message": "订单创建成功",
            "data": {"order": order}
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/orders", tags=["订单管理"])
async def list_orders(
    page: int = 1,
    page_size: int = 20
):
    """获取订单列表（用于GPS设备关联）"""
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
        
        orders = [dict(row) for row in cursor.fetchall()]
        
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


@app.put("/api/v1/orders/{order_id}/pickup", tags=["订单管理"])
async def mark_order_pickedup(order_id: int):
    """标记订单已提车（用于测试待安装GPS功能）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        current_time = datetime.now()
        
        cursor.execute("""
            UPDATE orders 
            SET status = 'picked_up', pickup_date = ?, updated_at = ?
            WHERE id = ?
        """, (current_time.date(), current_time, order_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        conn.commit()
        
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = dict(cursor.fetchone())
        
        return {
            "code": 200,
            "message": "订单已标记为已提车",
            "data": {"order": order}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
    finally:
        conn.close()


# ==================== 根路由 ====================

@app.get("/", tags=["系统信息"])
async def root():
    """根路由"""
    return {
        "message": "汽车分期管理平台 - GPS管理模块 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "devices": "/api/v1/gps/devices",
            "alerts": "/api/v1/gps/alerts",
            "dashboard": "/api/v1/gps/dashboard",
            "poll": "/api/v1/gps/poll"
        }
    }


@app.get("/health", tags=["系统信息"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "module": "GPS管理模块"
    }


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("=" * 50)
    print("🚀 GPS管理模块启动中...")
    print("=" * 50)
    init_database()
    print("✅ GPS管理模块启动完成")
    print("📖 API 文档: http://localhost:8001/docs")
    print("📖 ReDoc 文档: http://localhost:8001/redoc")
    print("=" * 50)


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动GPS管理模块 API 服务...")
    print("📖 API 文档: http://localhost:8001/docs")
    print("📖 ReDoc 文档: http://localhost:8001/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8001)
