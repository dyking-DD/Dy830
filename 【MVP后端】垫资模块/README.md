# 汽车分期管理平台 - 垫资管理模块 MVP 后端

## 项目概述

垫资管理模块是汽车分期管理平台的核心差异化功能，提供完整的垫资单生命周期管理，包括创建、审批、出账、还款和逾期检测等功能。

## 技术栈

- **语言**: Python 3.8+
- **框架**: FastAPI
- **数据库**: SQLite
- **数据验证**: Pydantic

## 项目结构

```
【MVP后端】垫资模块/
├── main.py          # FastAPI 应用入口，包含所有 API 路由
├── models.py        # Pydantic 数据模型定义
├── database.py      # SQLite 数据库连接和表创建
├── schemas.sql      # 数据库建表 SQL（备用）
├── requirements.txt # 项目依赖
└── README.md        # 项目说明文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn pydantic
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式一：直接运行
python main.py

# 方式二：使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口说明

### 订单管理

#### 创建测试订单
```
POST /api/v1/orders
```

**请求体示例**:
```json
{
  "customer_name": "张三",
  "customer_phone": "13800138001",
  "car_model": "特斯拉 Model 3",
  "car_price": 280000.00,
  "down_payment": 84000.00,
  "loan_amount": 196000.00
}
```

#### 获取订单列表
```
GET /api/v1/orders?page=1&page_size=20
```

### 垫资单管理

#### 1. 创建垫资单
```
POST /api/v1/advances
```

**请求体示例**:
```json
{
  "order_id": 1,
  "customer_name": "张三",
  "amount": 50000.00,
  "lender_type": "company",
  "lender_account": "公司账户A",
  "purpose": "首付垫资",
  "interest_rate_type": "monthly",
  "monthly_rate": 0.015,
  "start_date": "2024-01-01",
  "expected_repay_date": "2024-02-01"
}
```

#### 2. 垫资单列表
```
GET /api/v1/advances?page=1&page_size=20&status=disbursed&start_date=2024-01-01
```

**查询参数**:
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 100）
- `status`: 状态筛选（可选）
- `start_date`: 开始日期筛选（可选）
- `end_date`: 结束日期筛选（可选）

#### 3. 垫资单详情
```
GET /api/v1/advances/{advance_id}
```

#### 4. 垫资审批
```
POST /api/v1/advances/{advance_id}/approve
```

**请求体示例**:
```json
{
  "approver": "李经理",
  "approval_opinion": "同意垫资",
  "approved": true
}
```

**状态变更**: 待审批 → 审批通过 / 审批拒绝

#### 5. 垫资出账
```
POST /api/v1/advances/{advance_id}/disburse
```

**请求体示例**:
```json
{
  "disburse_time": "2024-01-01T10:00:00"
}
```

**状态变更**: 审批通过 → 已出账

#### 6. 垫资还款
```
POST /api/v1/advances/{advance_id}/repay
```

**请求体示例**:
```json
{
  "actual_repay_amount": 50750.00,
  "repay_time": "2024-02-01T15:00:00"
}
```

**自动计算利息**: 利息 = 垫资金额 × 日利率 × 实际天数

**状态变更**: 已出账 → 已还清（如果全额还款）

#### 7. 垫资仪表盘
```
GET /api/v1/advances/dashboard
```

**返回数据**:
- 当前垫资余额
- 今日新垫资（笔数、金额）
- 本月新垫资（笔数、金额）
- 待还垫资笔数
- 逾期笔数
- 近30天垫资余额趋势

#### 8. 逾期检测
```
POST /api/v1/advances/check-overdue
```

自动检测已过预计还款日但未还清的垫资单，标记为逾期状态。

## 垫资利息计算

### 计算公式
```
利息 = 垫资金额 × 日利率 × 实际天数
```

### 利率转换
- 月息转日息：日利率 = 月利率 / 30
- 默认月利率：1.5%（0.015）

### 计算示例
```
垫资金额：50,000元
月利率：1.5%
日利率：0.015 / 30 = 0.0005
实际天数：30天

利息 = 50,000 × 0.0005 × 30 = 750元
```

## 状态机

### 垫资单状态流转

```
待审批 (pending_approval)
    ↓ 审批通过
审批通过 (approved)
    ↓ 出账
已出账 (disbursed)
    ↓ 还款              ↓ 逾期
已还清 (repaid)      逾期 (overdue)
                        ↓ 还款
                    已还清 (repaid)

待审批 (pending_approval)
    ↓ 审批拒绝
审批拒绝 (rejected)
```

### 状态说明

| 状态 | 说明 | 允许操作 |
|------|------|---------|
| pending_approval | 待审批 | 审批 |
| approved | 审批通过 | 出账 |
| rejected | 审批拒绝 | 无 |
| disbursed | 已出账 | 还款 |
| repaid | 已还清 | 无 |
| overdue | 逾期 | 还款 |

## 数据库设计

### 订单表 (orders)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_no | TEXT | 订单号 |
| customer_name | TEXT | 客户姓名 |
| customer_phone | TEXT | 客户电话 |
| car_model | TEXT | 车型 |
| car_price | DECIMAL | 车辆价格 |
| down_payment | DECIMAL | 首付金额 |
| loan_amount | DECIMAL | 贷款金额 |
| status | TEXT | 订单状态 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 垫资单表 (advances)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| advance_no | TEXT | 垫资单号 |
| order_id | INTEGER | 关联订单ID |
| customer_name | TEXT | 客户姓名 |
| amount | DECIMAL | 垫资金额 |
| lender_type | TEXT | 垫资方类型（company/personal） |
| lender_account | TEXT | 垫资账户 |
| purpose | TEXT | 垫资用途 |
| interest_rate_type | TEXT | 利率类型（monthly/daily） |
| monthly_rate | DECIMAL | 月利率 |
| daily_rate | DECIMAL | 日利率 |
| start_date | DATE | 垫资开始日期 |
| expected_repay_date | DATE | 预计还款日期 |
| actual_repay_date | DATE | 实际还款日期 |
| actual_repay_amount | DECIMAL | 实际还款金额 |
| calculated_interest | DECIMAL | 计算利息 |
| status | TEXT | 垫资单状态 |
| approver | TEXT | 审批人 |
| approval_opinion | TEXT | 审批意见 |
| approval_time | TIMESTAMP | 审批时间 |
| disburse_time | TIMESTAMP | 出账时间 |
| repay_time | TIMESTAMP | 还款时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 统一响应格式

所有 API 返回统一的 JSON 格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

## 错误处理

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 400 | 请求参数错误或状态转换非法 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 开发说明

### 金额处理
- 所有金额使用 `Decimal` 类型，避免浮点精度问题
- 数据库使用 `DECIMAL(12, 2)` 存储

### 利率处理
- 月利率：`DECIMAL(5, 4)`，支持到小数点后4位
- 日利率：`DECIMAL(7, 6)`，支持到小数点后6位

### 日期时间处理
- 日期格式：`YYYY-MM-DD`
- 时间格式：`YYYY-MM-DDTHH:MM:SS`

### CORS 配置
- 已配置允许所有来源的跨域请求
- 生产环境请根据实际需求调整

## 生产环境建议

1. **数据库**: 建议升级到 PostgreSQL 或 MySQL
2. **认证授权**: 添加 JWT 或 OAuth2 认证
3. **日志**: 集成日志系统（如 ELK）
4. **监控**: 添加性能监控和告警
5. **容器化**: 使用 Docker 部署
6. **反向代理**: 使用 Nginx 作为反向代理

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
