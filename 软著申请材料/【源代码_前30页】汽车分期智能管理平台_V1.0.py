#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
汽车分期智能管理平台 V1.0 - 前30页源代码
计算机软件著作权登记 - 程序鉴别材料
============================================================================
版权所有：[开发单位名称]
版本：V1.0
开发时间：2026年4月

本系统实现以下核心功能：
1. 订单全生命周期管理（接单→审批→放款→提车→归档→完结）
2. 垫资智能管理（申请→审批→出账→计息→还款→逾期监控）
3. GPS设备实时监控（设备管理→定位追踪→告警中心→驾驶舱）
4. 资料智能归档（OCR识别→自动分类→状态追踪→归档管理）
5. 全链路通知引擎（节点触发→双端通知→逾期预警）
6. 银行审批接口预留（标准API→快速接入）
7. 数据驾驶舱（垫资余额→逾期率→GPS状态→经营报表）
8. 角色权限管理（多角色→精细权限→操作日志）

技术栈：Python 3 + FastAPI + SQLite + Pydantic + Redis
============================================================================
"""

# ============================================================================
# 第一部分：模块引用与配置
# ============================================================================

import os
import sys
import json
import math
import time
import datetime
import asyncio
import hashlib
import uuid
import random
import string
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager

# Web框架
try:
    from fastapi import FastAPI, HTTPException, Request, Depends, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi import FastAPI
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# 数据验证
try:
    from pydantic import BaseModel, Field, validator, root_validator
    from pydantic.dataclasses import dataclass as pydantic_dataclass
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

# 数据库
try:
    import sqlite3
    from typing import Generator
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

# 缓存
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# HTTP客户端
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ============================================================================
# 第二部分：枚举与常量定义
# ============================================================================

class OrderStage(str, Enum):
    """订单阶段枚举"""
    CREATED = "已接单"                    # 刚接单
    ADVANCE_PENDING = "垫资预审"          # 垫资申请中
    ADVANCE_APPROVAL = "垫资审批中"        # 垫资待审批
    ADVANCE_APPROVED = "垫资审批通过"      # 垫资已批准
    ADVANCE_DISBURSED = "垫资已出账"      # 垫资已打款
    ADVANCE_RETURNED = "垫资已还清"        # 垫资已还款
    BANK_PENDING = "银行审批中"           # 银行审批中（预留接口）
    BANK_APPROVED = "银行审批通过"        # 银行审批通过
    BANK_REJECTED = "银行审批拒绝"         # 银行拒绝
    LOAN_NOTIFIED = "放款通知"            # 银行放款，通知提车
    PENDING_PICKUP = "待提车"             # 待提车
    CAR_PICKED = "已提车"                # 已提车
    GPS_INSTALLING = "GPS安装中"          # GPS安装中
    GPS_ONLINE = "GPS已在线"             # GPS已上线
    ARCHIVE_PENDING = "资料归档中"        # 待收集资料
    ARCHIVE_COMPLETE = "归档完成"         # 资料归档完成
    MORTGAGE_PENDING = "抵押登记中"       # 抵押登记中
    MORTGAGE_COMPLETE = "已抵押"         # 已抵押
    NORMAL_REPAYING = "正常还款"          # 正常还款中
    OVERDUE = "逾期"                      # 逾期
    SETTLED = "已结清"                    # 结清
    COMPLETED = "已完结"                  # 全流程完结


class AdvanceStatus(str, Enum):
    """垫资状态枚举"""
    PENDING = "待审批"          # 待审批
    APPROVED = "审批通过"        # 已批准
    REJECTED = "审批拒绝"        # 已拒绝
    DISBURSED = "已出账"         # 资金已出
    RETURNED = "已还清"          # 已还款
    OVERDUE = "逾期"             # 逾期未还


class GPSStatus(str, Enum):
    """GPS设备状态枚举"""
    ONLINE = "在线"
    OFFLINE = "离线"
    WEAK_SIGNAL = "信号弱"
    ALERT = "告警中"


class AlertType(str, Enum):
    """GPS告警类型枚举"""
    SPEED = "超速告警"
    OUT_OF_ZONE = "出区域告警"
    POWER_OFF = "断电告警"
    DEVICE_REMOVED = "拆机告警"
    LOW_BATTERY = "低电量告警"
    SOS = "SOS紧急报警"


class ArchiveStatus(str, Enum):
    """归档状态枚举"""
    PENDING = "待上传"        # 未开始
    PARTIAL = "部分上传"      # 部分完成
    COMPLETE = "已完整"       # 全部上传
    OCR_PROCESSING = "OCR识别中"
    OCR_COMPLETE = "OCR已完成"
    ARCHIVED = "已归档"       # 最终归档


class NotificationChannel(str, Enum):
    """通知渠道枚举"""
    WECHAT = "微信服务号"
    SMS = "短信"
    APP_PUSH = "APP推送"
    SYSTEM = "系统消息"
    PHONE = "电话"


# ============================================================================
# 第三部分：配置管理
# ============================================================================

@dataclass
class SystemConfig:
    """系统配置"""
    system_name: str = "汽车分期智能管理平台"
    version: str = "V1.0"
    api_prefix: str = "/api/v1"

    # 数据库配置
    db_path: str = "./data/auto_finance.db"

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # 垫资配置
    advance_default_rate: float = 0.015    # 默认月利率1.5%
    advance_daily_rate: float = 0.0005    # 默认日利率万分之五
    advance_min_days: int = 1             # 最低计息天数
    advance_overdue_days: int = 7          # 逾期天数阈值

    # GPS配置
    gps_poll_interval: int = 300          # GPS轮询间隔（秒）
    gps_offline_threshold: int = 600       # 离线判定阈值（秒）

    # 通知配置
    sms_enabled: bool = True
    wechat_enabled: bool = True
    app_push_enabled: bool = True

    # 分页配置
    default_page_size: int = 20
    max_page_size: int = 100


class Config:
    """配置单例"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = SystemConfig()
        return cls._instance

    def get(self) -> SystemConfig:
        return self.config

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)


def get_config() -> SystemConfig:
    """获取配置"""
    return Config().get()


# ============================================================================
# 第四部分：数据模型（Pydantic）
# ============================================================================

# ─── 通用响应模型 ───

class APIResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[Any] = Field(None, description="数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": {}
            }
        }


class PageResult(BaseModel):
    """分页结果"""
    items: List[Any] = Field(default_factory=list)
    total: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")
    pages: int = Field(0, description="总页数")


# ─── 订单模型 ───

class CustomerInfo(BaseModel):
    """客户基本信息"""
    name: str = Field(..., min_length=2, max_length=50, description="客户姓名")
    phone: str = Field(..., regex=r"^1[3-9]\d{9}$", description="手机号")
    id_number: str = Field(..., regex=r"^\d{17}[\dXx]$", description="身份证号")
    address: Optional[str] = Field(None, max_length=200, description="地址")
    emergency_contact: Optional[str] = Field(None, max_length=50, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, regex=r"^1[3-9]\d{9}$", description="紧急联系人电话")


class CarInfo(BaseModel):
    """车辆信息"""
    brand: str = Field(..., min_length=1, max_length=50, description="汽车品牌")
    model: str = Field(..., min_length=1, max_length=100, description="车型")
    year: Optional[int] = Field(None, description="年款")
    vin: Optional[str] = Field(None, max_length=17, description="车架号")
    plate_number: Optional[str] = Field(None, max_length=20, description="车牌号")
    color: Optional[str] = Field(None, max_length=20, description="颜色")
    price: Decimal = Field(..., gt=0, description="车辆总价", decimal_places=2)


class LoanInfo(BaseModel):
    """贷款信息"""
    loan_amount: Decimal = Field(..., gt=0, description="贷款金额", decimal_places=2)
    down_payment: Decimal = Field(..., ge=0, description="首付金额", decimal_places=2)
    loan_period: int = Field(..., ge=6, le=60, description="贷款期数（月）")
    monthly_payment: Decimal = Field(..., ge=0, description="月供金额", decimal_places=2)
    interest_rate: Optional[Decimal] = Field(None, description="贷款利率（年化）", decimal_places=4)
    bank_name: Optional[str] = Field(None, max_length=50, description="贷款银行")
    bank_account: Optional[str] = Field(None, max_length=30, description="还款账户")


class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    customer: CustomerInfo
    car: CarInfo
    loan: LoanInfo
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str = Field(..., description="订单号")
    stage: str = Field(..., description="当前阶段")
    customer_name: str = Field(..., description="客户姓名")
    customer_phone: str = Field(..., description="客户手机")
    car_brand: str = Field(..., description="汽车品牌")
    car_model: str = Field(..., description="车型")
    car_price: Decimal = Field(..., description="车辆总价")
    loan_amount: Decimal = Field(..., description="贷款金额")
    down_payment: Decimal = Field(..., description="首付金额")
    monthly_payment: Decimal = Field(..., description="月供金额")
    loan_period: int = Field(..., description="贷款期数")
    created_by: str = Field(..., description="接单员工")
    created_at: str = Field(..., description="接单时间")
    stage_updated_at: Optional[str] = Field(None, description="阶段更新时间")


class OrderUpdateStageRequest(BaseModel):
    """更新订单阶段请求"""
    stage: OrderStage
    remark: Optional[str] = Field(None, max_length=500, description="阶段备注")


# ─── 垫资模型 ───

class AdvanceCreateRequest(BaseModel):
    """创建垫资请求"""
    order_id: str = Field(..., description="关联订单号")
    advance_amount: Decimal = Field(..., gt=0, description="垫资金额", decimal_places=2)
    payer_type: str = Field(..., regex="^(公司账户|个人账户)$", description="垫资方类型")
    payer_account: str = Field(..., max_length=50, description="垫资账户")
    purpose: str = Field(..., max_length=100, description="垫资用途")
    interest_rate: Optional[Decimal] = Field(None, description="月利率（默认1.5%）", decimal_places=4)
    start_date: str = Field(..., description="垫资起始日 YYYY-MM-DD")
    expected_repayment_date: str = Field(..., description="预计还款日 YYYY-MM-DD")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class AdvanceResponse(BaseModel):
    """垫资响应"""
    advance_id: str = Field(..., description="垫资单号")
    order_id: str = Field(..., description="关联订单号")
    customer_name: str = Field(..., description="客户姓名")
    advance_amount: Decimal = Field(..., description="垫资本金")
    interest_rate: Decimal = Field(..., description="月利率")
    days: int = Field(..., description="计息天数")
    interest_amount: Decimal = Field(..., description="利息合计")
    total_amount: Decimal = Field(..., description="本息合计")
    status: str = Field(..., description="状态")
    start_date: str = Field(..., description="起始日")
    expected_repayment_date: str = Field(..., description="预计还款日")
    actual_repayment_date: Optional[str] = Field(None, description="实际还款日")
    approver: Optional[str] = Field(None, description="审批人")
    created_by: str = Field(..., description="申请人")


class AdvanceApproveRequest(BaseModel):
    """垫资审批请求"""
    approved: bool = Field(..., description="是否批准")
    approver: str = Field(..., min_length=2, max_length=50, description="审批人姓名")
    opinion: Optional[str] = Field(None, max_length=200, description="审批意见")


class AdvanceRepayRequest(BaseModel):
    """垫资还款请求"""
    repayment_amount: Decimal = Field(..., gt=0, description="还款金额", decimal_places=2)
    repayment_date: Optional[str] = Field(None, description="实际还款日期")
    remark: Optional[str] = Field(None, max_length=200, description="还款备注")


class AdvanceDashboard(BaseModel):
    """垫资仪表盘"""
    total_balance: Decimal = Field(..., description="当前垫资余额")
    today_new_amount: Decimal = Field(..., description="今日新垫资")
    month_new_amount: Decimal = Field(..., description="本月新垫资")
    pending_count: int = Field(0, description="待还笔数")
    overdue_count: int = Field(0, description="逾期笔数")
    overdue_amount: Decimal = Field(..., description="逾期金额")
    recent_list: List[Dict] = Field(default_factory=list, description="近期垫资列表")
    balance_trend: List[Dict] = Field(default_factory=list, description="余额趋势")


# ─── GPS模型 ───

class GPSDeviceCreateRequest(BaseModel):
    """创建设备请求"""
    order_id: str = Field(..., description="关联订单号")
    imei: str = Field(..., regex=r"^\d{13,15}$", description="设备IMEI号")
    device_type: str = Field(..., regex="^(有线|无线|隐蔽)$", description="设备类型")
    install_location: str = Field(..., max_length=100, description="安装位置描述")
    install_staff: str = Field(..., min_length=2, max_length=50, description="安装人员")


class GPSDeviceResponse(BaseModel):
    """设备响应"""
    device_id: str = Field(..., description="设备编号")
    order_id: str = Field(..., description="关联订单号")
    customer_name: str = Field(..., description="客户姓名")
    imei: str = Field(..., description="设备IMEI")
    device_type: str = Field(..., description="设备类型")
    online_status: str = Field(..., description="在线状态")
    last_heartbeat: Optional[str] = Field(None, description="最后心跳时间")
    location: Optional[str] = Field(None, description="当前位置")
    alert_count: int = Field(0, description="未处理告警数")


class GPSAlertResponse(BaseModel):
    """GPS告警响应"""
    alert_id: str = Field(..., description="告警编号")
    device_id: str = Field(..., description="设备编号")
    alert_type: str = Field(..., description="告警类型")
    alert_time: str = Field(..., description="告警时间")
    location: Optional[str] = Field(None, description="告警位置")
    handled: bool = Field(False, description="是否已处理")
    handled_by: Optional[str] = Field(None, description="处理人")
    handled_time: Optional[str] = Field(None, description="处理时间")


class GPSDashboard(BaseModel):
    """GPS驾驶舱"""
    total_devices: int = Field(0, description="设备总数")
    online_count: int = Field(0, description="在线数")
    offline_count: int = Field(0, description="离线数")
    alert_count: int = Field(0, description="告警数")
    today_installed: int = Field(0, description="今日安装数")
    pending_install: int = Field(0, description="待安装数")
    recent_alerts: List[GPSAlertResponse] = Field(default_factory=list, description="最近告警")


# ─── 归档模型 ───

class ArchiveUploadRequest(BaseModel):
    """归档上传请求"""
    order_id: str = Field(..., description="关联订单号")
    document_type: str = Field(..., description="资料类型")
    file_name: str = Field(..., max_length=200, description="文件名")
    file_url: str = Field(..., description="文件URL")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    uploaded_by: str = Field(..., min_length=2, max_length=50, description="上传人")


class ArchiveItemResponse(BaseModel):
    """归档项响应"""
    document_id: str = Field(..., description="资料编号")
    order_id: str = Field(..., description="关联订单号")
    customer_name: str = Field(..., description="客户姓名")
    document_type: str = Field(..., description="资料类型")
    file_name: str = Field(..., description="文件名")
    file_url: str = Field(..., description="文件URL")
    ocr_result: Optional[Dict] = Field(None, description="OCR识别结果")
    upload_time: str = Field(..., description="上传时间")
    uploaded_by: str = Field(..., description="上传人")


class ArchiveStatusResponse(BaseModel):
    """归档状态响应"""
    order_id: str = Field(..., description="订单号")
    customer_name: str = Field(..., description="客户姓名")
    overall_status: str = Field(..., description="总体状态")
    progress_percent: int = Field(0, description="完成进度%")
    items: List[Dict] = Field(default_factory=list, description="各项状态")


# ─── 通知模型 ───

class NotificationSendRequest(BaseModel):
    """发送通知请求"""
    order_id: Optional[str] = Field(None, description="关联订单号")
    channel: NotificationChannel
    recipient: str = Field(..., max_length=50, description="接收人")
    recipient_phone: str = Field(..., regex=r"^1[3-9]\d{9}$", description="接收人手机")
    template_code: str = Field(..., description="模板编码")
    template_params: Dict[str, str] = Field(default_factory=dict, description="模板参数")
    content: str = Field(..., max_length=500, description="通知内容")


class NotificationLogResponse(BaseModel):
    """通知日志响应"""
    log_id: str = Field(..., description="日志编号")
    order_id: Optional[str] = Field(None, description="关联订单号")
    channel: str = Field(..., description="通知渠道")
    recipient: str = Field(..., description="接收人")
    content: str = Field(..., description="通知内容")
    status: str = Field(..., description="发送状态")
    sent_at: str = Field(..., description="发送时间")


# ─── 银行接口模型（预留） ───

class BankApprovalRequest(BaseModel):
    """银行审批请求"""
    order_id: str = Field(..., description="关联订单号")
    customer_id_number: str = Field(..., description="客户身份证号")
    car_vin: str = Field(..., description="车架号")
    loan_amount: Decimal = Field(..., description="贷款金额")
    loan_period: int = Field(..., description="贷款期数")
    bank_code: str = Field(..., description="银行编码")


class BankApprovalResponse(BaseModel):
    """银行审批响应"""
    bank_order_id: str = Field(..., description="银行订单号")
    status: str = Field(..., description="审批状态")
    reason: Optional[str] = Field(None, description="原因")
    approved_amount: Optional[Decimal] = Field(None, description="批准金额")
    approved_period: Optional[int] = Field(None, description="批准期数")


# ============================================================================
# 第五部分：数据库层
# ============================================================================

class Database:
    """数据库管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            config = get_config()
            db_path = config.db_path

        self.db_path = db_path
        self._ensure_dir()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_tables(self):
        """初始化所有表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. 系统用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sys_users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                real_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT,
                phone TEXT,
                status TEXT DEFAULT '正常',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 2. 客户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                id_number TEXT UNIQUE NOT NULL,
                address TEXT,
                emergency_contact TEXT,
                emergency_phone TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 3. 车辆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                car_id TEXT PRIMARY KEY,
                order_id TEXT UNIQUE,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER,
                vin TEXT UNIQUE,
                plate_number TEXT,
                color TEXT,
                price REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 4. 订单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT,
                car_id TEXT,
                stage TEXT NOT NULL DEFAULT '已接单',
                stage_remark TEXT,
                loan_amount REAL NOT NULL,
                down_payment REAL NOT NULL,
                loan_period INTEGER NOT NULL,
                monthly_payment REAL NOT NULL,
                interest_rate REAL,
                bank_name TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                stage_updated_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (car_id) REFERENCES cars(car_id)
            )
        """)

        # 5. 垫资表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advances (
                advance_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                advance_amount REAL NOT NULL,
                payer_type TEXT NOT NULL,
                payer_account TEXT NOT NULL,
                purpose TEXT,
                interest_rate REAL NOT NULL DEFAULT 0.015,
                start_date TEXT NOT NULL,
                expected_repayment_date TEXT NOT NULL,
                actual_repayment_date TEXT,
                interest_amount REAL DEFAULT 0,
                total_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT '待审批',
                approver TEXT,
                approver_opinion TEXT,
                approved_at TEXT,
                repaid_at TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 6. GPS设备表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gps_devices (
                device_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                imei TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                install_location TEXT,
                install_photo TEXT,
                install_staff TEXT,
                install_date TEXT,
                online_status TEXT DEFAULT '离线',
                last_heartbeat TEXT,
                current_location TEXT,
                battery_level INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 7. GPS告警表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gps_alerts (
                alert_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                alert_time TEXT NOT NULL,
                location TEXT,
                handled INTEGER DEFAULT 0,
                handled_by TEXT,
                handled_time TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 8. 归档资料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_documents (
                document_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_url TEXT NOT NULL,
                file_size INTEGER,
                ocr_result TEXT,
                upload_time TEXT DEFAULT (datetime('now')),
                uploaded_by TEXT NOT NULL
            )
        """)

        # 9. 归档清单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_checklists (
                checklist_id TEXT PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                id_card_front INTEGER DEFAULT 0,
                id_card_back INTEGER DEFAULT 0,
                driving_license INTEGER DEFAULT 0,
                vehicle_certificate INTEGER DEFAULT 0,
                gps_photos INTEGER DEFAULT 0,
                pickup_confirmation INTEGER DEFAULT 0,
                advance_agreement INTEGER DEFAULT 0,
                invoice INTEGER DEFAULT 0,
                insurance INTEGER DEFAULT 0,
                overall_status TEXT DEFAULT '待上传',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 10. 还款计划表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repayment_plans (
                plan_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                period_number INTEGER NOT NULL,
                due_date TEXT NOT NULL,
                due_amount REAL NOT NULL,
                actual_date TEXT,
                actual_amount REAL,
                status TEXT DEFAULT '正常',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 11. 通知日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                log_id TEXT PRIMARY KEY,
                order_id TEXT,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                template_code TEXT,
                content TEXT NOT NULL,
                status TEXT DEFAULT '待发送',
                sent_at TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 12. 银行申请记录表（预留接口）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_applications (
                application_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                bank_code TEXT NOT NULL,
                bank_name TEXT,
                bank_order_id TEXT,
                status TEXT DEFAULT '待提交',
                approved_amount REAL,
                approved_period INTEGER,
                reason TEXT,
                submitted_at TEXT,
                result_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 13. 操作日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                detail TEXT,
                ip_address TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # 创建索引
        self._create_indexes(cursor)

        conn.commit()
        conn.close()

    def _create_indexes(self, cursor):
        """创建索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_orders_stage ON orders(stage)",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_advances_order ON advances(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_advances_status ON advances(status)",
            "CREATE INDEX IF NOT EXISTS idx_gps_devices_order ON gps_devices(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_gps_devices_imei ON gps_devices(imei)",
            "CREATE INDEX IF NOT EXISTS idx_gps_alerts_device ON gps_alerts(device_id)",
            "CREATE INDEX IF NOT EXISTS idx_gps_alerts_time ON gps_alerts(alert_time)",
            "CREATE INDEX IF NOT EXISTS idx_archive_order ON archive_documents(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_notification_order ON notification_logs(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_repayment_order ON repayment_plans(order_id)",
        ]

        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
            except sqlite3.Error:
                pass

    def execute(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def execute_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """执行查询返回一条"""
        results = self.execute(sql, params)
        return results[0] if results else None

    def insert(self, sql: str, params: tuple = None) -> bool:
        """执行插入"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.rollback()
            conn.close()
            return False


# ============================================================================
# 第六部分：核心业务逻辑 - 订单服务
# ============================================================================

class OrderService:
    """订单服务"""

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def generate_order_id() -> str:
        """生成订单号：FP-YYYYMMDD-XXXX"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"FP-{today}-{random_part}"

    @staticmethod
    def generate_customer_id() -> str:
        """生成客户号"""
        return f"CUST-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    def generate_car_id() -> str:
        """生成车辆号"""
        return f"CAR-{uuid.uuid4().hex[:12].upper()}"

    def create_order(self, req: OrderCreateRequest, created_by: str) -> str:
        """创建订单"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            customer_id = self.generate_customer_id()
            car_id = self.generate_car_id()
            order_id = self.generate_order_id()
            now = datetime.datetime.now().isoformat()

            # 插入客户
            cursor.execute("""
                INSERT INTO customers (customer_id, name, phone, id_number, address, emergency_contact, emergency_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                req.customer.name,
                req.customer.phone,
                req.customer.id_number,
                req.customer.address,
                req.customer.emergency_contact,
                req.customer.emergency_phone
            ))

            # 插入车辆
            cursor.execute("""
                INSERT INTO cars (car_id, order_id, brand, model, year, vin, plate_number, color, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                car_id,
                order_id,
                req.car.brand,
                req.car.model,
                req.car.year,
                req.car.vin,
                req.car.plate_number,
                req.car.color,
                float(req.car.price)
            ))

            # 插入订单
            cursor.execute("""
                INSERT INTO orders (
                    order_id, customer_id, car_id, stage, loan_amount, down_payment,
                    loan_period, monthly_payment, interest_rate, bank_name, created_by, created_at, stage_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                customer_id,
                car_id,
                OrderStage.CREATED.value,
                float(req.loan.loan_amount),
                float(req.loan.down_payment),
                req.loan.loan_period,
                float(req.loan.monthly_payment),
                float(req.loan.interest_rate) if req.loan.interest_rate else None,
                req.loan.bank_name,
                created_by,
                now,
                now
            ))

            conn.commit()
            return order_id

        except sqlite3.Error as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
        finally:
            conn.close()

    def get_order_list(
        self,
        stage: Optional[str] = None,
        keyword: Optional[str] = """
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        car_id TEXT,
        stage TEXT NOT NULL DEFAULT '已接单',
        stage_remark TEXT,
        loan_amount REAL NOT NULL,
        down_payment REAL NOT NULL,
        loan_period INTEGER NOT NULL,
        monthly_payment REAL NOT NULL,
        interest_rate REAL,
        bank_name TEXT,
        created_by TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        stage_updated_at TEXT
    """
    ):
        """查询订单列表"""
        return order_id


class NotificationService:
    """通知服务"""

    def __init__(self, db: Database):
        self.db = db

    # 通知模板定义
    TEMPLATES = {
        "order_created": {
            "name": "订单已接单",
            "content": "您已提交分期申请，单号{order_id}，我们将在24小时内联系您。"
        },
        "advance_approved": {
            "name": "垫资审批通过",
            "content": "您的垫资申请已通过，金额{amount}元，预计{date}到账。"
        },
        "advance_disbursed": {
            "name": "垫资已出账",
            "content": "垫资{amount}元已出账，请知悉。"
        },
        "bank_approved": {
            "name": "银行审批通过",
            "content": "恭喜！您的分期申请已通过审核，可安排提车。"
        },
        "loan_notified": {
            "name": "放款通知提车",
            "content": "银行已放款，请前往{dealer}提车，联系人：{contact}。"
        },
        "gps_online": {
            "name": "GPS已在线",
            "content": "客户{customer}的GPS已在线，请收集抵押资料。"
        },
        "archive_complete": {
            "name": "资料归档完成",
            "content": "客户{customer}资料已归档完整，可提交抵押。"
        },
        "repayment_reminder": {
            "name": "还款提醒",
            "content": "您好，本月还款金额{amount}元，请于{date}日前存入还款账户。"
        },
        "overdue_warning_3d": {
            "name": "逾期3天提醒",
            "content": "您有一笔分期已逾期3天，请尽快处理，以免影响信用。"
        },
        "overdue_warning_7d": {
            "name": "逾期7天严重警告",
            "content": "严重提醒：您的分期已逾期7天，请立即处理，否则将采取法律措施。"
        },
        "settled": {
            "name": "结清通知",
            "content": "恭喜！您的分期已全部还清，请携带身份证前往办理解押。"
        }
    }
