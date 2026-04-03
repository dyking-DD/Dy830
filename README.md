# 汽车分期智能管理平台

统一后端服务，整合了所有业务模块，共享同一个SQLite数据库。

**现已增加权限控制：前台（客户）和后台（管理员）分离**

## 功能模块

### 核心业务
- **客户管理**: 客户创建、查询、列表
- **订单管理**: 订单创建、查询、阶段流转
- **垫资管理**: 垫资单创建、审批、出账、还款、逾期检测
- **GPS管理**: 设备注册、心跳监控、告警处理、驾驶舱
- **归档管理**: 资料上传、清单管理、OCR识别
- **还款管理**: 还款计划生成、还款记录录入、逾期检测
- **抵押管理**: 抵押登记、解押处理
- **通知服务**: 业务节点触发通知、日志查询、统计

### 权限控制
- **后台管理**: 需要管理员token，可查看和操作所有数据
- **前台客户**: 需要客户token，只能查看自己的数据
- **角色分离**: admin/boss/finance/collections/customer

### 驾驶舱
- **全局驾驶舱**: 全平台数据概览
- **模块驾驶舱**: 各模块独立数据统计

## 快速启动

### 方式一：使用启动脚本（推荐）

```bash
cd 【真实系统】汽车分期管理平台
./start.sh
```

### 方式二：手动启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python3 main.py
```

启动成功后访问：
- API文档：http://localhost:8899/docs
- ReDoc文档：http://localhost:8899/redoc

## 认证信息

### 后台管理员账号
- **超级管理员**: admin / admin123 （可看所有数据）
- **财务**: finance01 / finance123 （只能看垫资/还款）
- **贷后**: collections01 / collect123 （只能看GPS/归档/抵押）

### 前台客户账号
- **张三**: 手机号 13800138001 / 密码 123456
- **李四**: 手机号 13800138002 / 密码 123456

## API端点

### 认证管理
- `POST /api/v1/auth/login` - 管理员登录
- `POST /api/v1/auth/customer/login` - 客户登录
- `GET /api/v1/auth/me` - 获取当前用户信息

### 客户管理（需管理员token）
- `POST /api/v1/customers` - 创建客户
- `GET /api/v1/customers/{id}` - 获取客户详情
- `GET /api/v1/customers` - 获取客户列表

### 订单管理（需管理员token）
- `POST /api/v1/orders` - 创建订单
- `GET /api/v1/orders` - 获取订单列表
- `GET /api/v1/orders/{id}` - 获取订单详情
- `PUT /api/v1/orders/{id}/stage` - 更新订单阶段

### 垫资管理（需管理员token）
- `POST /api/v1/advances` - 创建垫资单
- `GET /api/v1/advances` - 获取垫资单列表
- `GET /api/v1/advances/{id}` - 获取垫资单详情
- `POST /api/v1/advances/{id}/approve` - 审批垫资单
- `POST /api/v1/advances/{id}/disburse` - 垫资出账
- `POST /api/v1/advances/{id}/repay` - 垫资还款
- `GET /api/v1/advances/dashboard` - 垫资仪表盘
- `POST /api/v1/advances/check-overdue` - 检测逾期

### GPS管理（需管理员token）
- `POST /api/v1/gps/devices` - 注册GPS设备
- `GET /api/v1/gps/devices` - 获取设备列表
- `POST /api/v1/gps/devices/{id}/heartbeat` - 设备心跳
- `GET /api/v1/gps/alerts` - 获取告警列表
- `POST /api/v1/gps/alerts` - 创建告警
- `POST /api/v1/gps/alerts/{id}/handle` - 处理告警
- `GET /api/v1/gps/dashboard` - GPS驾驶舱
- `POST /api/v1/gps/poll` - 模拟轮询

### 归档管理（需管理员token）
- `GET /api/v1/archive/checklists/{order_id}` - 获取归档清单
- `POST /api/v1/archive/documents` - 上传归档资料
- `GET /api/v1/archive/documents/{order_id}` - 获取已上传资料
- `POST /api/v1/archive/documents/{document_id}/ocr` - OCR识别
- `GET /api/v1/archive/stats` - 归档统计

### 还款管理（需管理员token）
- `POST /api/v1/repayments/plans/generate` - 生成还款计划
- `GET /api/v1/repayments/plans` - 获取还款计划列表
- `POST /api/v1/repayments/records` - 录入还款记录
- `GET /api/v1/repayments/stats` - 还款统计

### 抵押管理（需管理员token）
- `POST /api/v1/mortgage` - 创建抵押登记
- `GET /api/v1/mortgage` - 获取抵押列表
- `POST /api/v1/mortgage/{order_id}/release` - 解除抵押
- `GET /api/v1/mortgage/stats` - 抵押统计

### 通知管理（需管理员token）
- `GET /api/v1/notifications/templates` - 获取通知模板
- `POST /api/v1/notifications/send` - 发送通知
- `POST /api/v1/notifications/trigger` - 触发业务节点通知
- `GET /api/v1/notifications/logs` - 查询通知日志
- `GET /api/v1/notifications/stats` - 通知统计

### 驾驶舱（需管理员token）
- `GET /api/v1/dashboard` - 全局驾驶舱

### 客户前台（需客户token）
- `GET /api/v1/customer/orders` - 客户查看自己的订单列表
- `GET /api/v1/customer/orders/{order_id}` - 客户查看自己的订单详情
- `GET /api/v1/customer/advances` - 客户查看自己的垫资记录
- `GET /api/v1/customer/repayments` - 客户查看自己的还款计划
- `GET /api/v1/customer/documents` - 客户查看自己的资料归档状态
- `GET /api/v1/customer/dashboard` - 客户个人中心首页

### 管理员账户管理（需admin/boss角色）
- `POST /api/v1/admin/users` - 创建后台用户
- `GET /api/v1/admin/users` - 获取后台用户列表

### 系统
- `GET /` - 根路径
- `GET /health` - 健康检查

## 项目结构

```
【真实系统】汽车分期管理平台/
├── main.py                    # 统一入口，注册所有路由
├── database.py                # 统一数据库，所有表一次性创建
├── auth.py                    # 认证服务模块
├── models.py                  # 统一Pydantic模型
├── dingtalk.py                # 钉钉通知模块
├── requirements.txt           # Python依赖
├── start.sh                   # 一键启动脚本
├── README.md                  # 本文档
├── services/                  # 服务层
│   ├── __init__.py
│   ├── advance_service.py     # 垫资业务逻辑
│   ├── gps_service.py         # GPS业务逻辑
│   ├── archive_service.py     # 归档业务逻辑
│   ├── notification_service.py # 通知业务逻辑
│   └── mortgage_service.py    # 抵押业务逻辑
└── data/                      # 数据库文件目录
    └── car_loan_platform.db   # SQLite数据库
```

## 数据库表结构

系统包含以下数据表：

| 表名 | 说明 |
|------|------|
| customers | 客户表 |
| vehicles | 车辆表 |
| orders | 订单表 |
| advances | 垫资单表 |
| gps_devices | GPS设备表 |
| gps_alerts | GPS告警表 |
| archive_checklists | 归档清单表 |
| archive_documents | 归档资料表 |
| repayment_plans | 还款计划表 |
| repayment_records | 还款记录表 |
| mortgage | 抵押表 |
| notification_logs | 通知日志表 |
| **system_users** | **系统用户表（管理员）** |
| **customer_accounts** | **客户账户表（前台）** |

## 测试数据

系统启动时会自动创建测试数据：

- 3个客户（张三、李四、王五）
- 3个订单（不同阶段）
- 2个垫资单
- 2个GPS设备
- 1个归档清单
- 36期还款计划
- 1个抵押记录
- **3个后台管理员账号**
- **2个前台客户账号**

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLite
- **数据验证**: Pydantic
- **日期处理**: python-dateutil
- **认证方式**: SHA256哈希 + Token验证

## 统一响应格式

所有API返回统一的JSON格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

## 权限说明

### 后台管理员
- 所有后台路由需要管理员token
- Token通过 `POST /api/v1/auth/login` 登录获取
- 在请求Header中添加：`Authorization: Bearer <token>`

### 前台客户
- 所有客户路由需要客户token
- Token通过 `POST /api/v1/auth/customer/login` 登录获取
- 在请求Header中添加：`Authorization: Bearer <token>`
- 客户只能查看自己的数据（数据隔离）

## 注意事项

1. 首次启动会自动创建数据库和测试数据
2. 数据库文件位于 `data/car_loan_platform.db`
3. 如需重置数据，删除 `data/` 目录后重新启动即可
4. 默认端口为 8899，可在 `main.py` 中修改
5. 所有后台路由需要管理员认证
6. 所有前台路由需要客户认证

## 版本

v2.0.0 - 增加权限控制模块 |

## API端点

### 客户管理
- `POST /api/v1/customers` - 创建客户
- `GET /api/v1/customers/{id}` - 获取客户详情
- `GET /api/v1/customers` - 获取客户列表

### 订单管理
- `POST /api/v1/orders` - 创建订单
- `GET /api/v1/orders` - 获取订单列表
- `GET /api/v1/orders/{id}` - 获取订单详情
- `PUT /api/v1/orders/{id}/stage` - 更新订单阶段

### 垫资管理
- `POST /api/v1/advances` - 创建垫资单
- `GET /api/v1/advances` - 获取垫资单列表
- `GET /api/v1/advances/{id}` - 获取垫资单详情
- `POST /api/v1/advances/{id}/approve` - 审批垫资单
- `POST /api/v1/advances/{id}/disburse` - 垫资出账
- `POST /api/v1/advances/{id}/repay` - 垫资还款
- `GET /api/v1/advances/dashboard` - 垫资仪表盘
- `POST /api/v1/advances/check-overdue` - 检测逾期

### GPS管理
- `POST /api/v1/gps/devices` - 注册GPS设备
- `GET /api/v1/gps/devices` - 获取设备列表
- `POST /api/v1/gps/devices/{id}/heartbeat` - 设备心跳
- `GET /api/v1/gps/alerts` - 获取告警列表
- `POST /api/v1/gps/alerts` - 创建告警
- `POST /api/v1/gps/alerts/{id}/handle` - 处理告警
- `GET /api/v1/gps/dashboard` - GPS驾驶舱
- `POST /api/v1/gps/poll` - 模拟轮询

### 归档管理
- `GET /api/v1/archive/checklists/{order_id}` - 获取归档清单
- `POST /api/v1/archive/documents` - 上传归档资料
- `GET /api/v1/archive/documents/{order_id}` - 获取已上传资料
- `POST /api/v1/archive/documents/{document_id}/ocr` - OCR识别
- `GET /api/v1/archive/stats` - 归档统计

### 还款管理
- `POST /api/v1/repayments/plans/generate` - 生成还款计划
- `GET /api/v1/repayments/plans` - 获取还款计划列表
- `POST /api/v1/repayments/records` - 录入还款记录
- `GET /api/v1/repayments/stats` - 还款统计

### 抵押管理
- `POST /api/v1/mortgage` - 创建抵押登记
- `GET /api/v1/mortgage` - 获取抵押列表
- `POST /api/v1/mortgage/{order_id}/release` - 解除抵押
- `GET /api/v1/mortgage/stats` - 抵押统计

### 通知管理
- `GET /api/v1/notifications/templates` - 获取通知模板
- `POST /api/v1/notifications/send` - 发送通知
- `POST /api/v1/notifications/trigger` - 触发业务节点通知
- `GET /api/v1/notifications/logs` - 查询通知日志
- `GET /api/v1/notifications/stats` - 通知统计

### 驾驶舱
- `GET /api/v1/dashboard` - 全局驾驶舱

### 系统
- `GET /` - 根路径
- `GET /health` - 健康检查

## 测试数据

系统启动时会自动创建测试数据：

- 3个客户（张三、李四、王五）
- 3个订单（不同阶段）
- 2个垫资单
- 2个GPS设备
- 1个归档清单
- 36期还款计划
- 1个抵押记录

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLite
- **数据验证**: Pydantic
- **日期处理**: python-dateutil

## 统一响应格式

所有API返回统一的JSON格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

## 注意事项

1. 首次启动会自动创建数据库和测试数据
2. 数据库文件位于 `data/car_loan_platform.db`
3. 如需重置数据，删除 `data/` 目录后重新启动即可
4. 默认端口为 8888，可在 `main.py` 中修改

## 版本

v1.0.0
