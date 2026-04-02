# -*- coding: utf-8 -*-
"""
汽车分期智能管理平台 - 统一后端入口
整合所有模块：订单管理、垫资、GPS、归档、还款、抵押、通知
增加权限控制：前台（客户）和后台（管理员）分离
"""
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional, Dict
import uvicorn

# 导入数据库和模型
import database
import models

# 导入认证模块
from auth import hash_password, verify_password, generate_token, verify_token_full, get_user_from_db

# 导入服务
from services import advance_service
from services import gps_service
from services import archive_service
from services import notification_service
from services import mortgage_service
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# ==================== 创建FastAPI应用 ====================

app = FastAPI(
    title="汽车分期智能管理平台",
    description="""
## 汽车分期智能管理平台 API

统一后端服务，整合以下模块：

### 业务模块
- **客户管理**: 客户创建、查询
- **订单管理**: 订单创建、查询、阶段流转
- **垫资管理**: 垫资单创建、审批、出账、还款
- **GPS管理**: 设备注册、心跳监控、告警处理
- **归档管理**: 资料上传、清单管理、OCR识别
- **还款管理**: 还款计划生成、还款记录录入
- **抵押管理**: 抵押登记、解押处理
- **通知服务**: 业务节点触发通知、日志查询

### 驾驶舱
- **全局驾驶舱**: 全平台数据概览
- **模块驾驶舱**: 各模块独立数据统计
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# OAuth2 安全方案（让Swagger显示Authorize按钮）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

# 全局依赖，让Swagger UI显示Authorize按钮（仅文档，不强制验证）
async def optional_token(authorization: str = Header(None)):
    return authorization

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 为Swagger UI添加Authorize按钮
from fastapi.openapi.models import OAuth2

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = {
        "openapi": "3.0.2",
        "info": {
            "title": "汽车分期智能管理平台",
            "version": "1.0.0",
        },
        "paths": app.openapi_schema.get("paths", {}) if hasattr(app, 'openapi_schema') and app.openapi_schema else {},
        "components": {
            "securitySchemes": {
                "OAuth2PasswordBearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "description": "Bearer token认证。格式: Bearer <token>"
                }
            }
        },
    }
    return openapi_schema

# 覆盖默认的openapi
if not hasattr(app, 'openapi'):
    pass
app.openapi = custom_openapi


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("\n" + "="*60)
    print("🚀 汽车分期智能管理平台启动中...")
    print("="*60)
    database.init_database()
    print("✅ 数据库初始化完成")
    print("📖 API 文档: http://localhost:8899/docs")
    print("📖 ReDoc 文档: http://localhost:8899/redoc")
    print("="*60)
    print("🔐 认证信息：")
    print("  后台管理员：admin / admin123")
    print("  前台客户：手机号 13800138001 / 密码 123456")
    print("="*60 + "\n")


# ==================== 辅助函数 ====================

def api_response(code: int = 200, message: str = "success", data = None) -> dict:
    """统一API响应格式"""
    return {"code": code, "message": message, "data": data}


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


def verify_admin_token(authorization: Optional[str]) -> Dict:
    """验证管理员token，返回用户信息或抛出异常"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = verify_token_full(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="token无效或已过期")
    
    if user.get("role") == "customer":
        raise HTTPException(status_code=403, detail="仅限管理员访问")
    
    return user


def verify_customer_token(authorization: Optional[str]) -> Dict:
    """验证客户token，返回用户信息或抛出异常"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = verify_token_full(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="token无效或已过期")
    
    if user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="仅限客户访问")
    
    return user


# ==================== 认证路由 ====================

@app.post("/api/v1/auth/login", tags=["认证管理"], summary="管理员登录")
async def admin_login(req: models.LoginRequest):
    """管理员登录"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT user_id, username, password_hash, name, role, department FROM system_users WHERE username = ? AND status = '正常'",
            (req.username,)
        )
        user = cursor.fetchone()
        
        if not user or not verify_password(req.password, user['password_hash']):
            return api_response(code=401, message="用户名或密码错误")
        
        token = generate_token(user['user_id'], user['role'])
        
        return api_response(data={
            "token": token,
            "user_id": user['user_id'],
            "username": user['username'],
            "name": user['name'],
            "role": user['role'],
            "department": user['department']
        })
    finally:
        conn.close()


@app.post("/api/v1/auth/customer/login", tags=["认证管理"], summary="客户登录")
async def customer_login(req: models.CustomerLoginRequest):
    """客户登录"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT account_id, customer_id, password_hash, status FROM customer_accounts WHERE phone = ?",
            (req.phone,)
        )
        account = cursor.fetchone()
        
        if not account or not verify_password(req.password, account['password_hash']):
            return api_response(code=401, message="手机号或密码错误")
        
        if account['status'] != '正常':
            return api_response(code=403, message="账户已被禁用")
        
        token = generate_token(account['account_id'], "customer")
        
        # 获取客户姓名
        cursor.execute("SELECT name FROM customers WHERE customer_id = ?", (account['customer_id'],))
        customer = cursor.fetchone()
        
        return api_response(data={
            "token": token,
            "account_id": account['account_id'],
            "customer_id": account['customer_id'],
            "customer_name": customer['name'] if customer else "",
            "phone": req.phone
        })
    finally:
        conn.close()


@app.get("/api/v1/auth/me", tags=["认证管理"], summary="获取当前用户信息")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前用户信息"""
    if not authorization:
        return api_response(code=401, message="未登录")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = verify_token_full(token)
    
    if not user:
        return api_response(code=401, message="token无效或已过期")
    
    # 从数据库获取完整用户信息
    user_info = get_user_from_db(user['user_id'], user['role'])
    
    return api_response(data=user_info)


# ==================== 客户管理路由 ====================

@app.post("/api/v1/customers", tags=["客户管理"], summary="创建客户")
async def create_customer(customer: models.CustomerCreate, authorization: Optional[str] = Header(None)):
    """创建客户"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        customer_id = database.generate_id("CUS")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO customers (customer_id, name, phone, id_number, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (customer_id, customer.name, customer.phone, customer.id_number, customer.address, now))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        customer_row = cursor.fetchone()
        
        return api_response(data={"customer": row_to_dict(customer_row)})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建客户失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/customers/{customer_id}", tags=["客户管理"], summary="获取客户详情")
async def get_customer(customer_id: str, authorization: Optional[str] = Header(None)):
    """获取客户详情"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
        
        return api_response(data={"customer": row_to_dict(customer)})
    finally:
        conn.close()


@app.get("/api/v1/customers", tags=["客户管理"], summary="获取客户列表")
async def list_customers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), authorization: Optional[str] = Header(None)):
    """获取客户列表"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM customers")
        total = cursor.fetchone()["total"]
        
        offset = (page - 1) * page_size
        cursor.execute("SELECT * FROM customers ORDER BY created_at DESC LIMIT ? OFFSET ?", (page_size, offset))
        
        customers = [row_to_dict(row) for row in cursor.fetchall()]
        
        return api_response(data={"total": total, "page": page, "page_size": page_size, "items": customers})
    finally:
        conn.close()


# ==================== 订单管理路由 ====================

@app.post("/api/v1/orders", tags=["订单管理"], summary="创建订单")
async def create_order(order: models.OrderCreate, authorization: Optional[str] = Header(None)):
    """创建订单（简化版，自动创建关联客户和车辆）"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查或创建客户
        cursor.execute("SELECT customer_id FROM customers WHERE phone = ?", (order.customer_phone,))
        customer = cursor.fetchone()
        
        if customer:
            customer_id = customer["customer_id"]
        else:
            customer_id = database.generate_id("CUS")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO customers (customer_id, name, phone, id_number, address, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (customer_id, order.customer_name, order.customer_phone, 
                  order.customer_id_number, order.customer_address, now))
        
        order_id = database.generate_id("ORD")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_id, stage, loan_amount, down_payment,
                loan_period, monthly_payment, interest_rate, bank_name,
                created_by, created_at, stage_updated_at
            ) VALUES (?, ?, '已接单', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, customer_id, order.loan_amount, order.down_payment,
              order.loan_period, order.monthly_payment, order.interest_rate,
              order.bank_name, order.created_by, now, now))
        
        vehicle_id = database.generate_id("VEH")
        cursor.execute("""
            INSERT INTO vehicles (vehicle_id, order_id, brand, model, vin, plate_number, price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_id, order_id, order.car_brand, order.car_model, 
              order.car_vin, order.car_plate_number, order.car_price, now))
        
        conn.commit()
        
        cursor.execute("""
            SELECT o.*, c.name as customer_name, c.phone as customer_phone,
                   v.brand as car_brand, v.model as car_model, v.plate_number
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE o.order_id = ?
        """, (order_id,))
        
        return api_response(message="订单创建成功", data={"order": row_to_dict(cursor.fetchone())})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/orders", tags=["订单管理"], summary="获取订单列表")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stage: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """获取订单列表"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        conditions = []
        params = []
        
        if stage:
            conditions.append("o.stage = ?")
            params.append(stage)
        
        if keyword:
            conditions.append("(o.order_id LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        count_sql = f"SELECT COUNT(*) as total FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.id_number, c.address,
                   v.brand as car_brand, v.model as car_model, v.vin, v.plate_number
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE {where_clause}
            ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """
        cursor.execute(list_sql, params + [page_size, offset])
        
        return api_response(data={"total": total, "page": page, "page_size": page_size, "items": [row_to_dict(r) for r in cursor.fetchall()]})
    finally:
        conn.close()


@app.get("/api/v1/orders/{order_id}", tags=["订单管理"], summary="获取订单详情")
async def get_order(order_id: str, authorization: Optional[str] = Header(None)):
    """获取订单详情"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.id_number, c.address,
                   v.brand as car_brand, v.model as car_model, v.vin, v.plate_number, v.price as car_price
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE o.order_id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return api_response(data={"order": row_to_dict(order)})
    finally:
        conn.close()


@app.put("/api/v1/orders/{order_id}/stage", tags=["订单管理"], summary="更新订单阶段")
async def update_order_stage(order_id: str, stage_update: models.OrderStageUpdate, authorization: Optional[str] = Header(None)):
    """更新订单阶段"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="订单不存在")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE orders SET stage = ?, stage_remark = ?, stage_updated_at = ? WHERE order_id = ?",
                      (stage_update.new_stage, stage_update.remark, now, order_id))
        conn.commit()
        
        cursor.execute("SELECT o.*, c.name as customer_name FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_id = ?", (order_id,))
        return api_response(message="订单阶段更新成功", data={"order": row_to_dict(cursor.fetchone())})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()


# ==================== 垫资管理路由 ====================

@app.post("/api/v1/advances", tags=["垫资管理"], summary="创建垫资单")
async def create_advance(advance: models.AdvanceCreate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.create_advance(advance.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/advances", tags=["垫资管理"], summary="获取垫资单列表")
async def list_advances(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: Optional[str] = Query(None), order_id: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.get_advance_list(status=status, order_id=order_id, page=page, page_size=page_size)
    return api_response(data=result["data"])


@app.get("/api/v1/advances/{advance_id}", tags=["垫资管理"], summary="获取垫资单详情")
async def get_advance(advance_id: str, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.get_advance_detail(advance_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return api_response(data=result["data"])


@app.post("/api/v1/advances/{advance_id}/approve", tags=["垫资管理"], summary="审批垫资单")
async def approve_advance(advance_id: str, approve: models.AdvanceApprove, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.approve_advance(advance_id, approve.approver, approve.opinion, approve.approved)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.post("/api/v1/advances/{advance_id}/disburse", tags=["垫资管理"], summary="垫资出账")
async def disburse_advance(advance_id: str, disburse: models.AdvanceDisburse, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.disburse_advance(advance_id, disburse.disburse_by)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.post("/api/v1/advances/{advance_id}/repay", tags=["垫资管理"], summary="垫资还款")
async def repay_advance(advance_id: str, repay: models.AdvanceRepay, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.repay_advance(advance_id, repay.repayment_amount, repay.repayment_date, repay.remark)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/advances/dashboard", tags=["垫资管理"], summary="垫资仪表盘")
async def advance_dashboard(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.get_dashboard()
    return api_response(data=result["data"])


@app.post("/api/v1/advances/check-overdue", tags=["垫资管理"], summary="检测逾期垫资单")
async def check_advance_overdue(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = advance_service.check_overdue()
    return api_response(message=result["message"], data=result["data"])


# ==================== GPS管理路由 ====================

@app.post("/api/v1/gps/devices", tags=["GPS管理"], summary="注册GPS设备")
async def register_gps_device(device: models.GPSDeviceCreate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.register_device(device.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/gps/devices", tags=["GPS管理"], summary="获取设备列表")
async def list_gps_devices(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.get_device_list(status=status, page=page, page_size=page_size)
    return api_response(data=result["data"])


@app.post("/api/v1/gps/devices/{device_id}/heartbeat", tags=["GPS管理"], summary="设备心跳")
async def gps_heartbeat(device_id: str, heartbeat: models.GPSHeartbeat, authorization: Optional[str] = Header(None)):
    # 后台权限验证（设备心跳可以是匿名的，但建议验证）
    # verify_admin_token(authorization)
    
    result = gps_service.heartbeat(device_id, heartbeat.latitude, heartbeat.longitude, heartbeat.location)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/gps/alerts", tags=["GPS管理"], summary="获取告警列表")
async def list_gps_alerts(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), handled: Optional[bool] = Query(None), alert_type: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.get_alert_list(handled=handled, alert_type=alert_type, page=page, page_size=page_size)
    return api_response(data=result["data"])


@app.post("/api/v1/gps/alerts", tags=["GPS管理"], summary="创建GPS告警")
async def create_gps_alert(alert: models.GPSAlertCreate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.add_alert(alert.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.post("/api/v1/gps/alerts/{alert_id}/handle", tags=["GPS管理"], summary="处理告警")
async def handle_gps_alert(alert_id: str, handle: models.GPSAlertHandle, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.handle_alert(alert_id, handle.handled_by, handle.handle_note)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/gps/dashboard", tags=["GPS管理"], summary="GPS驾驶舱")
async def gps_dashboard(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.get_dashboard()
    return api_response(data=result["data"])


@app.post("/api/v1/gps/poll", tags=["GPS管理"], summary="模拟轮询设备状态")
async def poll_gps_status(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = gps_service.poll_status()
    return api_response(data=result["data"])


# ==================== 归档管理路由 ====================

@app.get("/api/v1/archive/checklists/{order_id}", tags=["归档管理"], summary="获取归档清单状态")
async def get_archive_checklist(order_id: str, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = archive_service.get_checklist(order_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return api_response(data=result["data"])


@app.post("/api/v1/archive/documents", tags=["归档管理"], summary="上传归档资料")
async def upload_archive_document(upload: models.ArchiveUpload, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = archive_service.upload_document(upload.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/archive/documents/{order_id}", tags=["归档管理"], summary="获取订单已上传资料")
async def get_archive_documents(order_id: str, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = archive_service.get_documents_by_order(order_id)
    return api_response(data=result["data"])


@app.post("/api/v1/archive/documents/{document_id}/ocr", tags=["归档管理"], summary="OCR识别资料")
async def ocr_archive_document(document_id: str, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = archive_service.ocr_document(document_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/archive/stats", tags=["归档管理"], summary="归档统计")
async def archive_stats(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = archive_service.get_stats()
    return api_response(data=result["data"])


# ==================== 还款管理路由 ====================

@app.post("/api/v1/repayments/plans/generate", tags=["还款管理"], summary="生成还款计划")
async def generate_repayment_plans(plan: models.RepaymentPlanGenerate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        from dateutil.relativedelta import relativedelta
        
        cursor.execute("SELECT o.order_id, c.name as customer_name FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_id = ?", (plan.order_id,))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_date = datetime.strptime(plan.start_date, "%Y-%m-%d")
        plans = []
        
        for i in range(plan.loan_period):
            plan_id = database.generate_id("RPP")
            due_date = start_date + relativedelta(months=i)
            
            cursor.execute("""
                INSERT INTO repayment_plans (plan_id, order_id, period_number, due_date, due_amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, '正常', ?)
            """, (plan_id, plan.order_id, i + 1, due_date.strftime("%Y-%m-%d"), plan.monthly_payment, now))
            
            plans.append({"plan_id": plan_id, "period_number": i + 1, "due_date": due_date.strftime("%Y-%m-%d"), "due_amount": plan.monthly_payment})
        
        conn.commit()
        
        return api_response(message=f"成功生成{plan.loan_period}期还款计划", data={"plans": plans, "customer_name": order["customer_name"]})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/repayments/plans", tags=["还款管理"], summary="获取还款计划列表")
async def list_repayment_plans(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), order_id: Optional[str] = Query(None), status: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        conditions = []
        params = []
        
        if order_id:
            conditions.append("rp.order_id = ?")
            params.append(order_id)
        
        if status:
            conditions.append("rp.status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f"SELECT COUNT(*) as total FROM repayment_plans rp WHERE {where_clause}", params)
        total = cursor.fetchone()["total"]
        
        offset = (page - 1) * page_size
        cursor.execute(f"""
            SELECT rp.*, o.customer_id, c.name as customer_name
            FROM repayment_plans rp
            LEFT JOIN orders o ON rp.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE {where_clause}
            ORDER BY rp.due_date DESC LIMIT ? OFFSET ?
        """, params + [page_size, offset])
        
        return api_response(data={"total": total, "page": page, "page_size": page_size, "items": [row_to_dict(r) for r in cursor.fetchall()]})
    finally:
        conn.close()


@app.post("/api/v1/repayments/records", tags=["还款管理"], summary="录入还款记录")
async def create_repayment_record(record: models.RepaymentRecordCreate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM repayment_plans WHERE plan_id = ?", (record.plan_id,))
        plan = cursor.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="还款计划不存在")
        
        plan_dict = row_to_dict(plan)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_id = database.generate_id("RPR")
        
        # 计算是否逾期
        due_date = datetime.strptime(plan_dict["due_date"], "%Y-%m-%d")
        repayment_date = datetime.strptime(record.repayment_date, "%Y-%m-%d")
        is_overdue = repayment_date > due_date
        
        # 插入还款记录
        cursor.execute("""
            INSERT INTO repayment_records (record_id, plan_id, order_id, actual_amount, repayment_date, payment_method, remark, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, record.plan_id, record.order_id, record.actual_amount, record.repayment_date, record.payment_method, record.remark, now))
        
        # 更新还款计划状态
        new_status = "逾期" if is_overdue else "已还清"
        cursor.execute("UPDATE repayment_plans SET status = ?, actual_date = ?, actual_amount = ? WHERE plan_id = ?",
                      (new_status, record.repayment_date, record.actual_amount, record.plan_id))
        
        # 检查是否所有期数都已还清
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = '已还清' THEN 1 ELSE 0 END) as repaid FROM repayment_plans WHERE order_id = ?", (record.order_id,))
        stats = cursor.fetchone()
        if stats["total"] == stats["repaid"]:
            cursor.execute("UPDATE orders SET stage = '已结清', stage_updated_at = ? WHERE order_id = ?", (now, record.order_id))
        
        conn.commit()
        
        return api_response(message="还款记录录入成功", data={"record_id": record_id, "status": new_status})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"录入失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/repayments/stats", tags=["还款管理"], summary="还款统计")
async def get_repayment_stats(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        # 今日待还
        cursor.execute("SELECT COALESCE(SUM(due_amount), 0) as total FROM repayment_plans WHERE due_date = ? AND status = '正常'", (today,))
        today_repayment = cursor.fetchone()["total"]
        
        # 本月待还
        cursor.execute("SELECT COALESCE(SUM(due_amount), 0) as total FROM repayment_plans WHERE due_date >= ? AND status = '正常'", (month_start,))
        month_repayment = cursor.fetchone()["total"]
        
        # 逾期统计
        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(due_amount), 0) as amount FROM repayment_plans WHERE status = '逾期'")
        overdue = cursor.fetchone()
        
        # 正常笔数
        cursor.execute("SELECT COUNT(*) as count FROM repayment_plans WHERE status = '正常'")
        normal_count = cursor.fetchone()["count"]
        
        return api_response(data={
            "today_repayment": today_repayment,
            "month_repayment": month_repayment,
            "overdue_count": overdue["count"],
            "overdue_amount": overdue["amount"],
            "normal_count": normal_count
        })
    finally:
        conn.close()


# ==================== 抵押管理路由 ====================

@app.post("/api/v1/mortgage", tags=["抵押管理"], summary="创建抵押登记")
async def create_mortgage(mortgage: models.MortgageCreate, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = mortgage_service.create_mortgage(mortgage.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/mortgage", tags=["抵押管理"], summary="获取抵押列表")
async def list_mortgages(order_id: Optional[str] = Query(None), status: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = mortgage_service.get_mortgage_list(order_id=order_id, status=status)
    return api_response(data=result["data"])


@app.post("/api/v1/mortgage/{order_id}/release", tags=["抵押管理"], summary="解除抵押")
async def release_mortgage(order_id: str, release: models.MortgageRelease, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = mortgage_service.release_mortgage(order_id, release.release_date)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/mortgage/stats", tags=["抵押管理"], summary="抵押统计")
async def mortgage_stats(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = mortgage_service.get_stats()
    return api_response(data=result["data"])


# ==================== 通知管理路由 ====================

@app.get("/api/v1/notifications/templates", tags=["通知管理"], summary="获取通知模板列表")
async def list_notification_templates(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    templates = notification_service.get_all_templates()
    return api_response(data={"templates": templates})


@app.post("/api/v1/notifications/send", tags=["通知管理"], summary="发送通知")
async def send_notification(notification: models.NotificationSend, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = notification_service.send_notification(notification.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.post("/api/v1/notifications/trigger", tags=["通知管理"], summary="触发业务节点通知")
async def trigger_notification(trigger: models.NotificationTrigger, authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = notification_service.trigger_notification(
        trigger.order_id, trigger.stage, trigger.channel, 
        trigger.recipient, trigger.recipient_phone, trigger.template_params
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return api_response(message=result["message"], data=result["data"])


@app.get("/api/v1/notifications/logs", tags=["通知管理"], summary="查询通知日志")
async def list_notification_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), order_id: Optional[str] = Query(None), channel: Optional[str] = Query(None), status: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = notification_service.get_logs(order_id=order_id, channel=channel, status=status, page=page, page_size=page_size)
    return api_response(data=result["data"])


@app.get("/api/v1/notifications/stats", tags=["通知管理"], summary="通知统计")
async def notification_stats(authorization: Optional[str] = Header(None)):
    # 后台权限验证
    verify_admin_token(authorization)
    
    result = notification_service.get_stats()
    return api_response(data=result["data"])


# ==================== 全局驾驶舱 ====================

@app.get("/api/v1/dashboard", tags=["驾驶舱"], summary="全局驾驶舱")
async def global_dashboard(authorization: Optional[str] = Header(None)):
    """获取全局驾驶舱数据"""
    # 后台权限验证
    verify_admin_token(authorization)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        # 订单统计
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_orders = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = ?", (today,))
        today_orders = cursor.fetchone()["count"]
        
        orders_stats = {"total": total_orders, "today_new": today_orders}
        
        # 垫资统计
        adv_result = advance_service.get_dashboard()
        advances_stats = adv_result["data"]
        
        # GPS统计
        gps_result = gps_service.get_dashboard()
        gps_stats = gps_result["data"]
        
        # 归档统计
        archive_result = archive_service.get_stats()
        archive_stats = archive_result["data"]
        
        # 还款统计
        cursor.execute("SELECT COUNT(*) as count FROM repayment_plans WHERE status = '正常'")
        normal_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(due_amount), 0) as amount FROM repayment_plans WHERE status = '逾期'")
        overdue = cursor.fetchone()
        repay_stats = {
            "normal_count": normal_count,
            "overdue_count": overdue["count"],
            "overdue_amount": overdue["amount"]
        }
        
        # 抵押统计
        mortgage_result = mortgage_service.get_stats()
        mortgage_stats = mortgage_result["data"]
        
        return api_response(data={
            "orders_stats": orders_stats,
            "advances_stats": advances_stats,
            "gps_stats": gps_stats,
            "archive_stats": archive_stats,
            "repayment_stats": repay_stats,
            "mortgage_stats": mortgage_stats
        })
    finally:
        conn.close()


# ==================== 前台客户路由（需 customer token）====================

@app.get("/api/v1/customer/orders", tags=["客户前台"], summary="客户查看自己的订单列表")
async def customer_get_orders(authorization: Optional[str] = Header(None)):
    """客户查看自己的订单列表"""
    user = verify_customer_token(authorization)
    customer_id = user.get("user_id")  # customer token的user_id就是account_id，需要查customer_id
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (customer_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        real_customer_id = account["customer_id"]
        
        cursor.execute("""
            SELECT o.*, c.name as customer_name, c.phone
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.customer_id = ?
            ORDER BY o.created_at DESC
        """, (real_customer_id,))
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        return api_response(data=orders)
    finally:
        conn.close()


@app.get("/api/v1/customer/orders/{order_id}", tags=["客户前台"], summary="客户查看自己的订单详情")
async def customer_get_order_detail(order_id: str, authorization: Optional[str] = Header(None)):
    """客户查看自己的订单详情"""
    user = verify_customer_token(authorization)
    account_id = user.get("user_id")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        customer_id = account["customer_id"]
        
        # 验证订单属于当前客户
        cursor.execute("""
            SELECT o.*, c.name as customer_name, c.phone, c.id_number, c.address,
                   v.brand as car_brand, v.model as car_model, v.vin, v.plate_number, v.price as car_price
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN vehicles v ON v.order_id = o.order_id
            WHERE o.order_id = ? AND o.customer_id = ?
        """, (order_id, customer_id))
        order = cursor.fetchone()
        
        if not order:
            return api_response(code=403, message="无权访问此订单")
        
        order_dict = row_to_dict(order)
        
        # 获取还款计划
        cursor.execute("SELECT * FROM repayment_plans WHERE order_id = ? ORDER BY period_number ASC", (order_id,))
        plans = [row_to_dict(row) for row in cursor.fetchall()]
        order_dict["repayment_plans"] = plans
        
        return api_response(data=order_dict)
    finally:
        conn.close()


@app.get("/api/v1/customer/advances", tags=["客户前台"], summary="客户查看自己的垫资记录")
async def customer_get_advances(authorization: Optional[str] = Header(None)):
    """客户查看自己的垫资记录"""
    user = verify_customer_token(authorization)
    account_id = user.get("user_id")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        customer_id = account["customer_id"]
        
        cursor.execute("""
            SELECT a.* FROM advances a
            JOIN orders o ON a.order_id = o.order_id
            WHERE o.customer_id = ?
            ORDER BY a.created_at DESC
        """, (customer_id,))
        advances = [row_to_dict(row) for row in cursor.fetchall()]
        
        return api_response(data=advances)
    finally:
        conn.close()


@app.get("/api/v1/customer/repayments", tags=["客户前台"], summary="客户查看自己的还款计划")
async def customer_get_repayments(authorization: Optional[str] = Header(None)):
    """客户查看自己的还款计划"""
    user = verify_customer_token(authorization)
    account_id = user.get("user_id")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        customer_id = account["customer_id"]
        
        cursor.execute("""
            SELECT rp.* FROM repayment_plans rp
            JOIN orders o ON rp.order_id = o.order_id
            WHERE o.customer_id = ?
            ORDER BY rp.period_number ASC
        """, (customer_id,))
        plans = [row_to_dict(row) for row in cursor.fetchall()]
        
        return api_response(data=plans)
    finally:
        conn.close()


@app.get("/api/v1/customer/documents", tags=["客户前台"], summary="客户查看自己的资料归档状态")
async def customer_get_documents(authorization: Optional[str] = Header(None)):
    """客户查看自己的资料归档状态"""
    user = verify_customer_token(authorization)
    account_id = user.get("user_id")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        customer_id = account["customer_id"]
        
        # 获取当前客户的所有订单ID
        cursor.execute("SELECT order_id FROM orders WHERE customer_id = ?", (customer_id,))
        order_ids = [row['order_id'] for row in cursor.fetchall()]
        
        documents = []
        for oid in order_ids:
            cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (oid,))
            checklist = cursor.fetchone()
            if checklist:
                documents.append(row_to_dict(checklist))
        
        return api_response(data=documents)
    finally:
        conn.close()


@app.get("/api/v1/customer/dashboard", tags=["客户前台"], summary="客户个人中心首页")
async def customer_dashboard(authorization: Optional[str] = Header(None)):
    """客户个人中心首页"""
    user = verify_customer_token(authorization)
    account_id = user.get("user_id")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 先获取customer_id
        cursor.execute("SELECT customer_id FROM customer_accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()
        if not account:
            return api_response(code=404, message="账户不存在")
        
        customer_id = account["customer_id"]
        
        # 客户姓名和电话
        cursor.execute("SELECT name, phone FROM customers WHERE customer_id = ?", (customer_id,))
        customer = cursor.fetchone()
        
        # 订单数量
        cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE customer_id = ?", (customer_id,))
        order_count = cursor.fetchone()['cnt']
        
        # 逾期数
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM repayment_plans rp
            JOIN orders o ON rp.order_id = o.order_id
            WHERE o.customer_id = ? AND rp.status = '逾期'
        """, (customer_id,))
        overdue_count = cursor.fetchone()['cnt']
        
        # 待还款金额
        cursor.execute("""
            SELECT COALESCE(SUM(due_amount), 0) as total
            FROM repayment_plans rp
            JOIN orders o ON rp.order_id = o.order_id
            WHERE o.customer_id = ? AND rp.status = '正常'
        """, (customer_id,))
        pending_amount = cursor.fetchone()['total']
        
        return api_response(data={
            "customer_name": customer['name'] if customer else "",
            "phone": customer['phone'] if customer else "",
            "order_count": order_count,
            "overdue_count": overdue_count,
            "pending_amount": pending_amount
        })
    finally:
        conn.close()


# ==================== 管理员账户管理 ====================

@app.post("/api/v1/admin/users", tags=["管理员账户"], summary="创建后台用户")
async def create_admin_user(req: models.AdminUserCreate, authorization: Optional[str] = Header(None)):
    """创建后台用户（仅admin角色）"""
    user = verify_admin_token(authorization)
    
    # 只有admin和boss可以创建用户
    if user.get("role") not in ["admin", "boss"]:
        return api_response(code=403, message="仅管理员可操作")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        import secrets as sec
        user_id = f"USER-{sec.token_hex(4).upper()}"
        password_hash = hash_password(req.password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO system_users (user_id, username, password_hash, name, role, department, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, '正常', ?)
        """, (user_id, req.username, password_hash, req.name, req.role, req.department, now))
        
        conn.commit()
        
        return api_response(message="用户创建成功", data={"user_id": user_id})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")
    finally:
        conn.close()


@app.get("/api/v1/admin/users", tags=["管理员账户"], summary="获取后台用户列表")
async def list_admin_users(authorization: Optional[str] = Header(None)):
    """获取后台用户列表"""
    user = verify_admin_token(authorization)
    
    # 只有admin和boss可以查看用户列表
    if user.get("role") not in ["admin", "boss"]:
        return api_response(code=403, message="仅管理员可操作")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, username, name, role, department, status, created_at FROM system_users ORDER BY created_at DESC")
        users = [row_to_dict(row) for row in cursor.fetchall()]
        
        return api_response(data=users)
    finally:
        conn.close()


# ==================== 系统路由 ====================

@app.get("/", tags=["系统"], summary="根路径")
async def root():
    return {
        "message": "汽车分期智能管理平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 启动汽车分期智能管理平台...")
    print("="*60)
    print("📖 API 文档: http://localhost:8899/docs")
    print("📖 ReDoc 文档: http://localhost:8899/redoc")
    print("="*60)
    print("🔐 认证信息：")
    print("  后台管理员：admin / admin123")
    print("  前台客户：手机号 13800138001 / 密码 123456")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8899)
