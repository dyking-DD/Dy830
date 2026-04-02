"""
Pydantic 数据模型定义
归档模块请求和响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================

class DocumentType(str, Enum):
    """资料类型枚举"""
    ID_CARD_FRONT = "id_card_front"           # 身份证人像面
    ID_CARD_BACK = "id_card_back"             # 身份证国徽面
    DRIVING_LICENSE = "driving_license"       # 行驶证
    VEHICLE_CERTIFICATE = "vehicle_certificate"  # 车辆登记证
    GPS_PHOTOS = "gps_photos"                 # GPS安装照片
    PICKUP_CONFIRMATION = "pickup_confirmation"  # 提车确认单
    ADVANCE_AGREEMENT = "advance_agreement"   # 垫资协议
    INVOICE = "invoice"                       # 购车发票（可选）
    INSURANCE = "insurance"                   # 保险单（可选）


class OverallStatus(str, Enum):
    """归档整体状态"""
    PENDING = "待上传"
    PARTIAL = "部分上传"
    COMPLETE = "已完整"


class UploadStatus(str, Enum):
    """单项上传状态"""
    UPLOADED = "已上传"
    PENDING = "待上传"


# ==================== 资料类型配置 ====================

# 标准资料类型映射：type -> (名称, 是否必填)
DOCUMENT_TYPE_CONFIG = {
    "id_card_front": {"name": "身份证人像面", "required": True},
    "id_card_back": {"name": "身份证国徽面", "required": True},
    "driving_license": {"name": "行驶证", "required": True},
    "vehicle_certificate": {"name": "车辆登记证", "required": True},
    "gps_photos": {"name": "GPS安装照片", "required": True},
    "pickup_confirmation": {"name": "提车确认单", "required": True},
    "advance_agreement": {"name": "垫资协议", "required": True},
    "invoice": {"name": "购车发票", "required": False},
    "insurance": {"name": "保险单", "required": False},
}

# 必填项列表
REQUIRED_DOCUMENTS = [
    "id_card_front",
    "id_card_back",
    "driving_license",
    "vehicle_certificate",
    "gps_photos",
    "pickup_confirmation",
    "advance_agreement",
]


# ==================== 请求模型 ====================

class ChecklistInitRequest(BaseModel):
    """初始化归档清单请求"""
    order_id: str = Field(..., description="订单ID")


class DocumentUploadRequest(BaseModel):
    """上传归档资料请求"""
    order_id: str = Field(..., description="订单ID")
    document_type: DocumentType = Field(..., description="资料类型")
    file_name: str = Field(..., description="文件名")
    file_url: str = Field(..., description="文件URL或本地路径")
    uploaded_by: str = Field(..., description="上传人")


# ==================== 响应模型 ====================

class ChecklistItem(BaseModel):
    """清单单项"""
    type: str = Field(..., description="资料类型代码")
    name: str = Field(..., description="资料名称")
    required: bool = Field(..., description="是否必填")
    status: str = Field(..., description="上传状态：已上传/待上传")


class ChecklistResponse(BaseModel):
    """归档清单响应"""
    order_id: str = Field(..., description="订单ID")
    customer_name: Optional[str] = Field(None, description="客户姓名")
    overall_status: str = Field(..., description="整体状态")
    progress_percent: int = Field(..., description="完成进度百分比")
    items: List[ChecklistItem] = Field(..., description="清单项目")


class DocumentResponse(BaseModel):
    """资料详情响应"""
    document_id: str = Field(..., description="资料ID")
    order_id: str = Field(..., description="订单ID")
    document_type: str = Field(..., description="资料类型")
    file_name: str = Field(..., description="文件名")
    file_url: str = Field(..., description="文件URL")
    ocr_result: Optional[dict] = Field(None, description="OCR识别结果")
    upload_time: Optional[str] = Field(None, description="上传时间")
    uploaded_by: Optional[str] = Field(None, description="上传人")


class DocumentGroupResponse(BaseModel):
    """按类型分组的资料响应"""
    document_type: str = Field(..., description="资料类型")
    type_name: str = Field(..., description="资料名称")
    documents: List[DocumentResponse] = Field(..., description="资料列表")


class OrderDocumentsResponse(BaseModel):
    """订单所有资料响应"""
    order_id: str = Field(..., description="订单ID")
    total_count: int = Field(..., description="资料总数")
    grouped_documents: List[DocumentGroupResponse] = Field(..., description="分组资料列表")


class ArchiveStatsResponse(BaseModel):
    """归档统计响应"""
    total_orders: int = Field(..., description="需要归档的订单总数")
    complete_count: int = Field(..., description="已完成归档数")
    partial_count: int = Field(..., description="部分上传数")
    pending_count: int = Field(..., description="待上传数")
    complete_rate: float = Field(..., description="归档完成率")
    missing_documents: List[dict] = Field(..., description="缺失最多的资料类型TOP3")


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[dict] = Field(None, description="数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
