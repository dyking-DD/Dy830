"""
汽车分期管理平台 - 订单与还款模块后端API
主程序入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import database

# 创建FastAPI应用
app = FastAPI(
    title="汽车分期管理平台 - 订单与还款模块",
    description="订单管理、还款管理、抵押管理、驾驶舱API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由
from routes import router

# 注册路由（统一前缀 /api/v1）
app.include_router(router, prefix="/api/v1")

# 启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    database.init_database()
    print("✅ 数据库初始化完成")

# 根路径
@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "message": "汽车分期管理平台 - 订单与还款模块 API",
        "docs": "/docs",
        "version": "1.0.0"
    }

# 健康检查
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式，自动重载
        log_level="info"
    )
