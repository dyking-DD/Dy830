# -*- coding: utf-8 -*-
"""
通知引擎 - FastAPI 主应用
汽车分期管理平台通知服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from notification_routes import router as notification_router
import uvicorn

# 创建FastAPI应用
app = FastAPI(
    title="汽车分期管理平台 - 通知引擎",
    description="""
## 通知引擎API文档

为汽车分期管理平台提供完整的通知服务，包括：

### 功能模块
- **通知模板管理**: 查询和获取通知模板
- **发送通知**: 单条和批量发送通知
- **业务节点触发**: 根据业务阶段自动触发通知
- **通知日志**: 查询和管理发送日志
- **统计分析**: 发送数据统计和分析

### 支持的通知渠道
- 微信推送 (wechat)
- 短信通知 (sms)
- APP推送 (app_push)
- 系统消息 (system)

### 业务场景覆盖
接单成功、垫资审批、银行审批、放款通知、提车通知、GPS上线、
归档完成、还款提醒、逾期提醒、结清通知等全流程通知服务。
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(notification_router)


# 根路径
@app.get("/", tags=["根路径"])
async def root():
    """API根路径"""
    return {
        "service": "汽车分期管理平台 - 通知引擎",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "notification-engine"
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 启动通知引擎服务...")
    print("="*60)
    print("📍 API文档: http://localhost:8000/docs")
    print("📍 ReDoc文档: http://localhost:8000/redoc")
    print("="*60 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
