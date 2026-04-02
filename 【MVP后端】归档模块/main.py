"""
FastAPI 应用入口
汽车分期管理平台 - 资料归档模块 MVP 后端
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 导入路由
from archive_routes import router as archive_router

# 创建 FastAPI 应用
app = FastAPI(
    title="汽车分期管理平台 - 资料归档模块",
    description="""
## 资料归档模块 MVP 后端 API

### 功能模块

1. **归档清单管理**
   - 初始化归档清单
   - 获取订单归档清单状态

2. **资料上传**
   - 上传归档资料
   - 自动更新清单状态

3. **归档状态查询**
   - 获取订单所有已上传资料
   - 获取资料详情

4. **OCR模拟接口**
   - 模拟OCR识别
   - 支持身份证、行驶证、车辆登记证等

5. **归档进度统计**
   - 整体归档进度
   - 缺失资料TOP3

### 资料类型

| 类型代码 | 名称 | 必填 |
|---------|------|-----|
| id_card_front | 身份证人像面 | ✓ |
| id_card_back | 身份证国徽面 | ✓ |
| driving_license | 行驶证 | ✓ |
| vehicle_certificate | 车辆登记证 | ✓ |
| gps_photos | GPS安装照片 | ✓ |
| pickup_confirmation | 提车确认单 | ✓ |
| advance_agreement | 垫资协议 | ✓ |
| invoice | 购车发票 | ✗ |
| insurance | 保险单 | ✗ |
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
app.include_router(archive_router)


# ==================== 系统路由 ====================

@app.get("/", tags=["系统信息"])
async def root():
    """根路由"""
    return {
        "message": "汽车分期管理平台 - 资料归档模块 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["系统信息"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "module": "archive"
    }


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动资料归档模块 API 服务...")
    print("📖 API 文档: http://localhost:8001/docs")
    print("📖 ReDoc 文档: http://localhost:8001/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8001)
