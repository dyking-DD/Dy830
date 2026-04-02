# 汽车分期管理平台 - 通知引擎

## 项目简介

通知引擎是汽车分期管理平台的核心模块之一，提供完整的通知服务功能，支持多种通知渠道和业务场景。

## 功能特性

### 1. 通知模板管理
- 查询所有通知模板
- 获取单个模板详情
- 内置13种业务场景模板

### 2. 发送通知
- 单条发送
- 批量发送
- 模拟发送（测试环境）

### 3. 业务节点触发
根据业务阶段自动匹配模板并发送通知，支持的阶段：
- 接单成功 (order_created)
- 垫资审批通过 (advance_approved)
- 垫资已出账 (advance_disbursed)
- 银行审批通过 (bank_approved)
- 放款通知 (loan_notified)
- 已提车 (car_picked)
- GPS已在线 (gps_online)
- 资料归档完成 (archive_complete)
- 抵押完成 (mortgage_complete)
- 还款提醒 (repayment_reminder)
- 逾期3天 (overdue_3d)
- 逾期7天 (overdue_7d)
- 已结清 (settled)

### 4. 通知日志
- 日志查询（支持多条件筛选）
- 日志详情
- 分页支持

### 5. 统计分析
- 今日/本周/本月发送量
- 各渠道发送统计
- 发送成功率

## 技术栈

- **Python 3.8+**
- **FastAPI** - Web框架
- **SQLite** - 数据库
- **Pydantic** - 数据验证

## 安装和运行

### 1. 安装依赖

```bash
cd 【MVP后端】通知引擎
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 模板管理
- `GET /api/v1/notifications/templates` - 获取所有模板
- `GET /api/v1/notifications/templates/{template_code}` - 获取模板详情

### 发送通知
- `POST /api/v1/notifications/send` - 发送单条通知
- `POST /api/v1/notifications/batch` - 批量发送
- `POST /api/v1/notifications/trigger` - 业务节点触发

### 日志管理
- `GET /api/v1/notifications/logs` - 查询日志列表
- `GET /api/v1/notifications/logs/{log_id}` - 获取日志详情

### 统计分析
- `GET /api/v1/notifications/stats` - 获取统计数据

## 使用示例

### 1. 发送接单通知

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/send" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD202401010001",
    "channel": "wechat",
    "recipient": "张三",
    "recipient_phone": "13800138000",
    "template_code": "order_created",
    "template_params": {"order_id": "ORD202401010001"}
  }'
```

### 2. 业务节点触发

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "order_created",
    "order_id": "ORD202401010001",
    "recipient": "张三",
    "recipient_phone": "13800138000",
    "channel": "wechat",
    "template_params": {"order_id": "ORD202401010001"}
  }'
```

### 3. 查询日志

```bash
curl "http://localhost:8000/api/v1/notifications/logs?order_id=ORD202401010001&page=1&page_size=20"
```

### 4. 获取统计

```bash
curl "http://localhost:8000/api/v1/notifications/stats"
```

## 项目结构

```
【MVP后端】通知引擎/
├── main.py                      # 主应用入口
├── models.py                    # 数据模型（Pydantic）
├── database.py                  # 数据库初始化
├── notification_service.py      # 服务层（业务逻辑）
├── notification_routes.py       # 路由层（API端点）
├── requirements.txt             # 依赖包列表
├── README.md                    # 项目说明文档
└── data/                        # 数据库文件目录
    └── notification.db          # SQLite数据库文件
```

## 内置通知模板

| 模板编码 | 模板名称 | 模板内容 |
|---------|---------|---------|
| order_created | 接单通知 | 您已提交分期申请，单号{order_id}，我们将在24小时内联系您。 |
| advance_approved | 垫资审批通过 | 您的垫资申请已通过，金额{amount}元，预计{date}到账。 |
| advance_disbursed | 垫资已出账 | 垫资{amount}元已出账，请知悉。 |
| bank_approved | 银行审批通过 | 恭喜！您的分期申请已通过审核，可安排提车。 |
| loan_notified | 放款通知提车 | 银行已放款，请前往{dealer}提车，联系人：{contact}。 |
| gps_online | GPS已在线 | 您的车辆GPS已在线，设备IMEI：{imei}，如有问题请联系客服。 |
| archive_complete | 归档完成 | 您的资料已归档完成，本月还款{amount}元，请按时还款。 |
| repayment_reminder | 还款提醒 | 您好，本月还款金额{amount}元，请于{date}日前存入还款账户。 |
| overdue_3d | 逾期3天提醒 | 您有一笔分期已逾期3天，请尽快处理，以免影响信用。 |
| overdue_7d | 逾期7天警告 | 严重提醒：您的分期已逾期7天，请立即处理，否则将采取法律措施。 |
| settled | 结清通知 | 恭喜！您的分期已全部还清，请携带身份证前往办理解押。 |

## 响应格式

所有API接口统一返回格式：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

## 注意事项

1. **模拟发送**: 当前版本为模拟发送，仅记录日志，不实际调用第三方API
2. **数据持久化**: 使用SQLite数据库，数据文件位于 `data/notification.db`
3. **生产环境**: 生产环境需配置实际的通知渠道API（微信、短信等）
4. **错误处理**: 所有异常会被捕获并返回友好的错误信息

## 后续扩展

- [ ] 集成真实的微信、短信、APP推送API
- [ ] 添加通知模板管理界面
- [ ] 支持自定义通知模板
- [ ] 添加通知失败重试机制
- [ ] 支持定时通知和延迟发送
- [ ] 添加用户通知偏好设置

## 版本历史

- v1.0.0 (2024-01-01)
  - 初始版本
  - 完成基础通知功能
  - 支持业务节点触发
  - 内置13种通知模板

## 联系方式

如有问题或建议，请联系开发团队。
