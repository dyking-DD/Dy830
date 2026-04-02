# 汽车分期管理平台 - 订单与还款模块

## 项目简介

这是汽车分期管理平台的订单管理和还款管理模块后端API，基于 FastAPI + SQLite 开发，提供完整的订单生命周期管理、还款计划管理、抵押登记管理等功能。

## 技术栈

- Python 3.8+
- FastAPI - 现代高性能Web框架
- SQLite - 轻量级数据库
- Pydantic - 数据验证
- Uvicorn - ASGI服务器

## 功能模块

### A. 订单管理

- ✅ 订单列表（分页、筛选、搜索）
- ✅ 订单详情查询
- ✅ 订单阶段更新（严格状态机检查）
- ✅ 订单创建

**订单阶段流转规则：**
```
已接单 → 垫资预审 → 垫资审批中 → 垫资通过 → 垫资已出账 → 垫资已还清
    ↓
银行审批中 → 审批通过 / 审批拒绝
    ↓
放款通知 → 待提车 → 已提车 → GPS安装中 → GPS已在线
    ↓
资料归档中 → 归档完成 → 抵押登记中 → 已抵押
    ↓
正常还款中 → 逾期 → 已结清 → 已完结
```

### B. 还款管理

- ✅ 还款计划生成
- ✅ 还款计划查询
- ✅ 还款记录录入
- ✅ 逾期自动检测
- ✅ 还款统计

### C. 抵押管理

- ✅ 抵押登记
- ✅ 抵押查询
- ✅ 解押操作
- ✅ 抵押统计

### D. 驾驶舱

- ✅ 全局数据汇总
- ✅ 订单统计
- ✅ 还款统计
- ✅ 抵押统计

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

### 3. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口列表

### 订单管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/orders | 创建订单 |
| GET | /api/v1/orders | 订单列表 |
| GET | /api/v1/orders/{order_id} | 订单详情 |
| PUT | /api/v1/orders/{order_id}/stage | 更新订单阶段 |

### 还款管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/repayments/plans/generate | 生成还款计划 |
| GET | /api/v1/repayments/plans | 还款计划列表 |
| GET | /api/v1/repayments/plans/{plan_id} | 还款计划详情 |
| POST | /api/v1/repayments/records | 录入还款记录 |
| GET | /api/v1/repayments/records | 还款记录列表 |
| GET | /api/v1/repayments/check-overdue | 检测逾期 |
| GET | /api/v1/repayments/stats | 还款统计 |

### 抵押管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/mortgage | 创建抵押登记 |
| GET | /api/v1/mortgage | 抵押列表 |
| GET | /api/v1/mortgage/{order_id} | 抵押详情 |
| POST | /api/v1/mortgage/{order_id}/release | 解除抵押 |
| GET | /api/v1/mortgage/stats | 抵押统计 |

### 驾驶舱

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/dashboard | 全局驾驶舱 |

## 统一响应格式

所有接口返回统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

## 数据库表结构

### orders（订单表）

- order_id: 订单ID（主键）
- customer_name: 客户姓名
- customer_phone: 客户电话
- customer_id_number: 身份证号
- car_brand: 车辆品牌
- car_model: 车辆型号
- car_vin: 车架号
- car_plate_number: 车牌号
- car_price: 车辆价格
- stage: 订单阶段
- loan_amount: 贷款金额
- down_payment: 首付金额
- loan_period: 贷款期数
- monthly_payment: 月供金额
- interest_rate: 利率
- bank_name: 贷款银行
- created_by: 创建人
- created_at: 创建时间
- stage_updated_at: 阶段更新时间

### repayment_plans（还款计划表）

- plan_id: 计划ID（主键）
- order_id: 订单ID（外键）
- period_number: 期数
- due_date: 应还日期
- due_amount: 应还金额
- actual_date: 实还日期
- actual_amount: 实还金额
- status: 状态（正常/逾期/已还清）
- overdue_days: 逾期天数
- created_at: 创建时间

### repayment_records（还款记录表）

- record_id: 记录ID（主键）
- plan_id: 计划ID（外键）
- order_id: 订单ID（外键）
- actual_amount: 实还金额
- repayment_date: 实还日期
- payment_method: 支付方式
- remark: 备注
- created_at: 创建时间

### mortgage（抵押登记表）

- mortgage_id: 抵押ID（主键）
- order_id: 订单ID（外键）
- mortgage_bank: 抵押银行
- register_date: 登记日期
- expire_date: 到期日期
- certificate_number: 登记证编号
- status: 状态（抵押中/已解押）
- release_date: 解押日期
- created_at: 创建时间

## 使用示例

### 1. 创建订单

```bash
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "张三",
    "customer_phone": "13800138000",
    "car_brand": "宝马",
    "car_model": "X5",
    "loan_amount": 300000,
    "down_payment": 100000,
    "loan_period": 36,
    "monthly_payment": 8888.88,
    "created_by": "系统管理员"
  }'
```

### 2. 查询订单列表

```bash
curl "http://localhost:8000/api/v1/orders?page=1&page_size=10"
```

### 3. 更新订单阶段

```bash
curl -X PUT "http://localhost:8000/api/v1/orders/ORD202401011234567890/stage" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "垫资预审",
    "remark": "客户资料已提交，进入垫资预审阶段"
  }'
```

### 4. 生成还款计划

```bash
curl -X POST "http://localhost:8000/api/v1/repayments/plans/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD202401011234567890",
    "loan_amount": 300000,
    "loan_period": 36,
    "start_date": "2024-02-15",
    "monthly_payment": 8888.88
  }'
```

### 5. 录入还款记录

```bash
curl -X POST "http://localhost:8000/api/v1/repayments/records" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "RPP202401011234567890",
    "actual_amount": 8888.88,
    "repayment_date": "2024-02-15",
    "payment_method": "银行转账",
    "remark": "第1期还款"
  }'
```

## 注意事项

1. **订单阶段流转**：系统严格检查状态流转规则，不允许越级流转
2. **还款计划**：生成后自动计算每月还款日（起始日 + n个月）
3. **逾期检测**：需要定期调用 `/api/v1/repayments/check-overdue` 接口进行逾期检测
4. **自动状态更新**：所有期数还清后，订单自动更新为"已结清"；解押后自动更新为"已完结"

## 开发说明

- 数据库文件：`car_loan.db`（SQLite）
- 开发模式：支持热重载
- 生产部署：建议使用 Gunicorn + Uvicorn

## 许可证

MIT License
