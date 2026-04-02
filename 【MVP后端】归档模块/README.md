# 汽车分期管理平台 - 资料归档模块

资料归档模块 MVP 后端 API，用于管理汽车分期业务的资料归档流程。

## 功能特性

### 1. 归档清单管理
- ✅ 初始化归档清单
- ✅ 获取订单归档清单状态
- ✅ 自动计算进度百分比

### 2. 资料上传
- ✅ 上传归档资料
- ✅ 自动更新清单状态
- ✅ 支持多种资料类型

### 3. 归档状态查询
- ✅ 获取订单所有已上传资料
- ✅ 按资料类型分组展示
- ✅ 获取资料详情

### 4. OCR识别
- ✅ 模拟OCR识别
- ✅ 支持身份证、行驶证、车辆登记证等
- ✅ 结果存储到数据库

### 5. 归档统计
- ✅ 整体归档进度
- ✅ 缺失资料TOP3统计
- ✅ 完成率计算

## 资料类型

### 必填资料（7项）
| 类型代码 | 名称 |
|---------|------|
| id_card_front | 身份证人像面 |
| id_card_back | 身份证国徽面 |
| driving_license | 行驶证 |
| vehicle_certificate | 车辆登记证 |
| gps_photos | GPS安装照片 |
| pickup_confirmation | 提车确认单 |
| advance_agreement | 垫资协议 |

### 可选资料（2项）
| 类型代码 | 名称 |
|---------|------|
| invoice | 购车发票 |
| insurance | 保险单 |

## 快速开始

### 安装依赖

```bash
pip install fastapi uvicorn pydantic
```

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8001` 启动

### API文档

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API接口

### 归档清单

#### 初始化归档清单
```
POST /api/v1/archive/checklists
```

请求体：
```json
{
  "order_id": "FP-20260402-0001"
}
```

#### 获取归档清单状态
```
GET /api/v1/archive/checklists/{order_id}
```

响应示例：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "FP-20260402-0001",
    "customer_name": "张三",
    "overall_status": "部分上传",
    "progress_percent": 50,
    "items": [
      {"type": "id_card_front", "name": "身份证人像面", "required": true, "status": "已上传"},
      {"type": "id_card_back", "name": "身份证国徽面", "required": true, "status": "待上传"}
    ]
  }
}
```

### 资料上传

#### 上传归档资料
```
POST /api/v1/archive/documents
```

请求体：
```json
{
  "order_id": "FP-20260402-0001",
  "document_type": "id_card_front",
  "file_name": "张三_身份证人像面.jpg",
  "file_url": "/uploads/2024/04/张三_身份证人像面.jpg",
  "uploaded_by": "业务员A"
}
```

#### 获取订单所有资料
```
GET /api/v1/archive/documents/{order_id}
```

#### 获取资料详情
```
GET /api/v1/archive/documents/detail/{document_id}
```

### OCR识别

#### 模拟OCR识别
```
POST /api/v1/archive/documents/{document_id}/ocr
```

响应示例：
```json
{
  "code": 200,
  "message": "OCR识别成功",
  "data": {
    "document_id": "DOC-20240402123456-1234",
    "document_type": "id_card_front",
    "type_name": "身份证人像面",
    "ocr_result": {
      "name": "张三",
      "gender": "男",
      "id_number": "110101199001011234",
      "address": "北京市朝阳区XX路XX号"
    }
  }
}
```

### 归档统计

#### 获取归档统计
```
GET /api/v1/archive/stats
```

响应示例：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_orders": 10,
    "complete_count": 5,
    "partial_count": 3,
    "pending_count": 2,
    "complete_rate": 50.0,
    "missing_documents": [
      {"type": "vehicle_certificate", "name": "车辆登记证", "missing_count": 5},
      {"type": "advance_agreement", "name": "垫资协议", "missing_count": 4},
      {"type": "gps_photos", "name": "GPS安装照片", "missing_count": 3}
    ]
  }
}
```

## 数据库结构

### 归档清单表 (archive_checklists)
| 字段 | 类型 | 说明 |
|-----|------|------|
| checklist_id | TEXT | 主键 |
| order_id | TEXT | 订单ID（唯一） |
| customer_name | TEXT | 客户姓名 |
| id_card_front | INTEGER | 身份证人像面上传状态 (0/1) |
| id_card_back | INTEGER | 身份证国徽面上传状态 (0/1) |
| ... | ... | 其他资料项 |
| overall_status | TEXT | 整体状态 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 归档资料表 (archive_documents)
| 字段 | 类型 | 说明 |
|-----|------|------|
| document_id | TEXT | 主键 |
| order_id | TEXT | 订单ID |
| document_type | TEXT | 资料类型 |
| file_name | TEXT | 文件名 |
| file_url | TEXT | 文件URL |
| ocr_result | TEXT | OCR结果（JSON） |
| upload_time | TEXT | 上传时间 |
| uploaded_by | TEXT | 上传人 |

## 运行测试

```bash
# 先启动服务
python main.py

# 在另一个终端运行测试
python test_api.py
```

## 项目结构

```
【MVP后端】归档模块/
├── main.py              # FastAPI 应用入口
├── database.py          # 数据库连接和表创建
├── models.py            # Pydantic 数据模型
├── archive_service.py   # 业务逻辑层
├── archive_routes.py    # API 路由层
├── test_api.py          # API 测试脚本
├── README.md            # 项目说明文档
└── data/                # SQLite 数据库文件目录
    └── archive_management.db
```

## 技术栈

- Python 3.8+
- FastAPI - Web 框架
- SQLite - 数据库
- Pydantic - 数据验证
- Uvicorn - ASGI 服务器
