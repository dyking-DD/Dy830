# API 使用示例

本文档提供详细的API使用示例，包括请求参数和响应格式。

## 基础信息

- **服务地址**: http://localhost:8000
- **API前缀**: /api/v1/notifications
- **文档地址**: http://localhost:8000/docs

## 统一响应格式

所有接口统一返回以下格式：

```json
{
  "code": 200,          // 状态码：200成功，其他为错误
  "message": "操作成功",  // 提示信息
  "data": { ... }       // 响应数据
}
```

---

## 1. 获取所有通知模板

### 请求

```http
GET /api/v1/notifications/templates
```

### 示例

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/templates"
```

### 响应

```json
{
  "code": 200,
  "message": "获取模板列表成功",
  "data": [
    {
      "template_code": "order_created",
      "name": "接单通知",
      "content_template": "您已提交分期申请，单号{order_id}，我们将在24小时内联系您。",
      "channel": "system",
      "remark": "客户提交分期申请后触发"
    },
    ...
  ]
}
```

---

## 2. 获取单个模板详情

### 请求

```http
GET /api/v1/notifications/templates/{template_code}
```

### 参数

- `template_code`: 模板编码（路径参数）

### 示例

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/templates/order_created"
```

### 响应

```json
{
  "code": 200,
  "message": "获取模板详情成功",
  "data": {
    "template_code": "order_created",
    "name": "接单通知",
    "content_template": "您已提交分期申请，单号{order_id}，我们将在24小时内联系您。",
    "channel": "system",
    "remark": "客户提交分期申请后触发"
  }
}
```

---

## 3. 发送单条通知

### 请求

```http
POST /api/v1/notifications/send
Content-Type: application/json
```

### 请求体

```json
{
  "order_id": "ORD202401010001",           // 可选，订单ID
  "channel": "wechat",                     // 必填，通知渠道
  "recipient": "张三",                      // 必填，接收人姓名
  "recipient_phone": "13800138000",        // 必填，接收人手机
  "template_code": "order_created",        // 可选，模板编码
  "template_params": {                     // 可选，模板参数
    "order_id": "ORD202401010001"
  },
  "content": "您已提交分期申请..."          // 可选，完整内容
}
```

### 示例

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

### 响应

```json
{
  "code": 200,
  "message": "发送通知成功",
  "data": {
    "log_id": "LOG20240101135200abc12345",
    "status": "已发送",
    "message": "通过wechat渠道发送成功"
  }
}
```

---

## 4. 批量发送通知

### 请求

```http
POST /api/v1/notifications/batch
Content-Type: application/json
```

### 请求体

```json
{
  "notifications": [
    {
      "order_id": "ORD202401010001",
      "channel": "wechat",
      "recipient": "张三",
      "recipient_phone": "13800138000",
      "template_code": "order_created",
      "template_params": {"order_id": "ORD202401010001"}
    },
    {
      "order_id": "ORD202401010002",
      "channel": "sms",
      "recipient": "李四",
      "recipient_phone": "13900139000",
      "template_code": "bank_approved",
      "template_params": {}
    }
  ]
}
```

### 示例

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "notifications": [
      {
        "order_id": "ORD202401010001",
        "channel": "wechat",
        "recipient": "张三",
        "recipient_phone": "13800138000",
        "template_code": "order_created",
        "template_params": {"order_id": "ORD202401010001"}
      }
    ]
  }'
```

### 响应

```json
{
  "code": 200,
  "message": "批量发送完成",
  "data": {
    "total": 2,
    "success_count": 2,
    "failed_count": 0,
    "results": [
      {
        "log_id": "LOG20240101135200abc12345",
        "status": "已发送",
        "message": "通过wechat渠道发送成功"
      },
      {
        "log_id": "LOG20240101135201def67890",
        "status": "已发送",
        "message": "通过sms渠道发送成功"
      }
    ]
  }
}
```

---

## 5. 业务节点触发通知（核心功能）

### 请求

```http
POST /api/v1/notifications/trigger
Content-Type: application/json
```

### 请求体

```json
{
  "stage": "order_created",                // 必填，业务阶段
  "order_id": "ORD202401010001",           // 必填，订单ID
  "recipient": "张三",                      // 必填，接收人姓名
  "recipient_phone": "13800138000",        // 必填，接收人手机
  "channel": "wechat",                     // 可选，默认system
  "template_params": {                     // 可选，模板参数
    "order_id": "ORD202401010001"
  }
}
```

### 支持的业务阶段

| stage | 说明 | 所需参数 |
|-------|------|---------|
| order_created | 接单成功 | order_id |
| advance_approved | 垫资审批通过 | amount, date |
| advance_disbursed | 垫资已出账 | amount |
| bank_approved | 银行审批通过 | - |
| loan_notified | 放款通知 | dealer, contact |
| car_picked | 已提车 | - |
| gps_online | GPS已在线 | imei |
| archive_complete | 归档完成 | amount |
| mortgage_complete | 抵押完成 | - |
| repayment_reminder | 还款提醒 | amount, date |
| overdue_3d | 逾期3天 | - |
| overdue_7d | 逾期7天 | - |
| settled | 已结清 | - |

### 示例1：接单成功通知

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

### 示例2：垫资审批通过通知

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "advance_approved",
    "order_id": "ORD202401010002",
    "recipient": "李四",
    "recipient_phone": "13900139000",
    "channel": "sms",
    "template_params": {
      "amount": "50000",
      "date": "2024-01-05"
    }
  }'
```

### 示例3：放款通知提车

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "loan_notified",
    "order_id": "ORD202401010003",
    "recipient": "王五",
    "recipient_phone": "13700137000",
    "channel": "wechat",
    "template_params": {
      "dealer": "北京4S店",
      "contact": "赵经理 13800000000"
    }
  }'
```

### 响应

```json
{
  "code": 200,
  "message": "触发通知成功",
  "data": {
    "log_id": "LOG20240101135200abc12345",
    "status": "已发送",
    "message": "通过wechat渠道发送成功"
  }
}
```

---

## 6. 查询通知日志

### 请求

```http
GET /api/v1/notifications/logs
```

### 查询参数

- `order_id`: 订单ID筛选（可选）
- `channel`: 渠道筛选（可选：wechat/sms/app_push/system）
- `status`: 状态筛选（可选：已发送/发送失败/待发送）
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）

### 示例1：查询所有日志

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs?page=1&page_size=20"
```

### 示例2：按订单ID筛选

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs?order_id=ORD202401010001"
```

### 示例3：按渠道筛选

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs?channel=wechat"
```

### 示例4：按状态筛选

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs?status=已发送"
```

### 示例5：组合筛选

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs?order_id=ORD202401010001&channel=wechat&status=已发送&page=1&page_size=10"
```

### 响应

```json
{
  "code": 200,
  "message": "查询日志成功",
  "data": {
    "total": 25,
    "page": 1,
    "page_size": 20,
    "logs": [
      {
        "log_id": "LOG20240101135200abc12345",
        "order_id": "ORD202401010001",
        "channel": "wechat",
        "recipient": "张三",
        "recipient_phone": "13800138000",
        "template_code": "order_created",
        "content": "您已提交分期申请，单号ORD202401010001，我们将在24小时内联系您。",
        "status": "已发送",
        "sent_at": "2024-01-01 13:52:00",
        "error_message": null,
        "created_at": "2024-01-01 13:52:00"
      },
      ...
    ]
  }
}
```

---

## 7. 获取日志详情

### 请求

```http
GET /api/v1/notifications/logs/{log_id}
```

### 参数

- `log_id`: 日志ID（路径参数）

### 示例

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/logs/LOG20240101135200abc12345"
```

### 响应

```json
{
  "code": 200,
  "message": "获取日志详情成功",
  "data": {
    "log_id": "LOG20240101135200abc12345",
    "order_id": "ORD202401010001",
    "channel": "wechat",
    "recipient": "张三",
    "recipient_phone": "13800138000",
    "template_code": "order_created",
    "content": "您已提交分期申请，单号ORD202401010001，我们将在24小时内联系您。",
    "status": "已发送",
    "sent_at": "2024-01-01 13:52:00",
    "error_message": null,
    "created_at": "2024-01-01 13:52:00"
  }
}
```

---

## 8. 获取通知统计

### 请求

```http
GET /api/v1/notifications/stats
```

### 示例

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/stats"
```

### 响应

```json
{
  "code": 200,
  "message": "获取统计数据成功",
  "data": {
    "today_sent": 15,
    "week_sent": 128,
    "month_sent": 456,
    "by_channel": {
      "wechat": 180,
      "sms": 120,
      "app_push": 90,
      "system": 66
    },
    "success_rate": 95.5
  }
}
```

---

## 错误响应

当请求出错时，返回格式：

```json
{
  "code": 400,
  "message": "错误描述",
  "data": null
}
```

### 常见错误码

- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 使用Python调用示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/notifications"

# 发送通知
response = requests.post(f"{BASE_URL}/send", json={
    "order_id": "ORD202401010001",
    "channel": "wechat",
    "recipient": "张三",
    "recipient_phone": "13800138000",
    "template_code": "order_created",
    "template_params": {"order_id": "ORD202401010001"}
})

print(response.json())
```

---

## 使用JavaScript调用示例

```javascript
const BASE_URL = "http://localhost:8000/api/v1/notifications";

// 发送通知
fetch(`${BASE_URL}/send`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    order_id: "ORD202401010001",
    channel: "wechat",
    recipient: "张三",
    recipient_phone: "13800138000",
    template_code: "order_created",
    template_params: { order_id: "ORD202401010001" }
  })
})
.then(response => response.json())
.then(data => console.log(data));
```
