# GPS管理模块 MVP 后端

汽车分期管理平台 - GPS设备管理后端API

## 功能概览

### 1. GPS设备管理
- 设备注册（关联订单）
- 设备列表查询（分页、状态筛选）
- 设备详情查询
- 设备位置获取

### 2. GPS心跳与状态
- 设备心跳上报
- 在线状态管理
- 超时自动离线（5分钟无心跳）

### 3. GPS告警管理
- 告警创建
- 告警列表查询
- 告警处理

### 4. GPS驾驶舱
- 设备总数统计
- 在线/离线/告警数量
- 今日安装数
- 待安装数
- 最近告警列表

### 5. GPS轮询模拟
- 模拟设备状态变化
- 模拟产生告警

## 技术栈

- Python 3 + FastAPI
- SQLite 数据库
- Pydantic 数据验证

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1：使用启动脚本
chmod +x start.sh
./start.sh

# 方式2：直接运行
python3 main.py

# 方式3：使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. 访问API文档

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API 接口

### GPS设备管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/gps/devices | 注册GPS设备 |
| GET | /api/v1/gps/devices | 获取设备列表 |
| GET | /api/v1/gps/devices/{device_id} | 获取设备详情 |
| GET | /api/v1/gps/devices/{device_id}/location | 获取设备位置 |

### GPS心跳与状态

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/gps/devices/{device_id}/heartbeat | 设备心跳 |
| POST | /api/v1/gps/devices/{device_id}/offline | 标记离线 |
| POST | /api/v1/gps/check-offline | 检查离线设备 |

### GPS告警管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/gps/alerts | 添加告警 |
| GET | /api/v1/gps/alerts | 获取告警列表 |
| POST | /api/v1/gps/alerts/{alert_id}/handle | 处理告警 |

### GPS驾驶舱

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/gps/dashboard | 驾驶舱数据 |

### GPS轮询模拟

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/gps/poll | 模拟轮询设备 |

## 数据模型

### 设备类型 (device_type)
- `wired`: 有线
- `wireless`: 无线
- `hidden`: 隐蔽

### 在线状态 (online_status)
- `在线`: 设备正常在线
- `离线`: 设备离线
- `告警中`: 设备有未处理告警

### 告警类型 (alert_type)
- `overspeed`: 超速告警
- `out_of_zone`: 出区域告警
- `power_off`: 断电告警
- `tamper`: 拆机告警
- `low_battery`: 低电量告警
- `sos`: SOS报警

## ID生成规则

### 设备ID
格式：`GPS-XXXX-XXXX`
示例：`GPS-1234-5678`

### 告警ID
格式：`ALT-YYYYMMDD-XXXX`
示例：`ALT-20250402-1234`

## 测试流程

### 1. 创建测试订单

```bash
curl -X POST "http://localhost:8001/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "张三", "customer_phone": "13800138000", "car_model": "丰田凯美瑞"}'
```

### 2. 注册GPS设备

```bash
curl -X POST "http://localhost:8001/api/v1/gps/devices" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "imei": "867584030012345",
    "device_type": "wired",
    "install_location": "仪表盘下方",
    "install_staff": "李师傅"
  }'
```

### 3. 发送心跳

```bash
curl -X POST "http://localhost:8001/api/v1/gps/devices/GPS-1234-5678/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 31.2304,
    "longitude": 121.4737,
    "address": "上海市浦东新区"
  }'
```

### 4. 创建告警

```bash
curl -X POST "http://localhost:8001/api/v1/gps/alerts" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "GPS-1234-5678",
    "alert_type": "overspeed",
    "latitude": 31.2304,
    "longitude": 121.4737,
    "address": "上海市浦东新区"
  }'
```

### 5. 处理告警

```bash
curl -X POST "http://localhost:8001/api/v1/gps/alerts/ALT-20250402-1234/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "handled_by": "王经理",
    "handle_note": "已联系客户，确认超速原因"
  }'
```

### 6. 查看驾驶舱

```bash
curl "http://localhost:8001/api/v1/gps/dashboard"
```

### 7. 模拟轮询

```bash
curl "http://localhost:8001/api/v1/gps/poll"
```

## 数据库结构

### gps_devices 表
- id: 主键
- device_id: 设备ID
- order_id: 关联订单ID
- imei: 设备IMEI
- device_type: 设备类型
- install_location: 安装位置
- install_staff: 安装人员
- online_status: 在线状态
- last_heartbeat: 最后心跳时间
- latitude/longitude: 经纬度
- address: 地址

### gps_alerts 表
- id: 主键
- alert_id: 告警ID
- device_id: 设备ID
- alert_type: 告警类型
- latitude/longitude: 告警位置
- alert_time: 告警时间
- handled: 是否已处理
- handled_by: 处理人
- handle_time: 处理时间

## 文件说明

```
【MVP后端】GPS模块/
├── main.py           # FastAPI应用入口
├── gps_routes.py     # API路由定义
├── gps_service.py    # 服务逻辑和数据库操作
├── requirements.txt  # Python依赖
├── start.sh          # 启动脚本
├── README.md         # 说明文档
├── test_api.py       # 测试脚本
└── data/             # SQLite数据库目录
    └── gps_management.db
```

## 注意事项

1. 本模块为MVP版本，使用SQLite数据库，适合测试和演示
2. 生产环境建议使用MySQL/PostgreSQL
3. 设备心跳超时时间默认为5分钟，可根据需求调整
4. 轮询模拟功能仅用于测试，生产环境请对接真实GPS设备

## 版本历史

- v1.0.0 (2025-04-02): 初始版本，实现基础GPS管理功能
