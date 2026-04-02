"""
归档模块路由层 - API接口定义
包含归档清单管理、资料上传、OCR识别、统计等接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import (
    ApiResponse, ChecklistInitRequest, DocumentUploadRequest,
    DocumentType
)
from archive_service import (
    init_checklist, get_checklist, upload_document,
    get_documents_by_order, get_document_detail, process_ocr,
    get_archive_stats
)

# 创建路由器
router = APIRouter(prefix="/api/v1/archive", tags=["归档管理"])


# ==================== 归档清单管理 ====================

@router.post("/checklists", response_model=ApiResponse, summary="初始化归档清单")
async def create_checklist(request: ChecklistInitRequest):
    """
    初始化归档清单
    
    - **order_id**: 订单ID（必填）
    
    自动生成checklist_id，初始所有项目状态为"待上传"
    """
    result = init_checklist(request.order_id)
    
    if not result["success"]:
        return ApiResponse(code=400, message=result["message"], data=result.get("data"))
    
    return ApiResponse(code=200, message=result["message"], data=result["data"])


@router.get("/checklists/{order_id}", response_model=ApiResponse, summary="获取归档清单状态")
async def get_order_checklist(order_id: str):
    """
    获取订单归档清单状态
    
    - **order_id**: 订单ID
    
    返回清单中每项的完成状态和整体进度百分比
    """
    result = get_checklist(order_id)
    
    if not result["success"]:
        return ApiResponse(code=404, message=result["message"], data=None)
    
    return ApiResponse(code=200, message=result["message"], data=result["data"])


# ==================== 资料上传 ====================

@router.post("/documents", response_model=ApiResponse, summary="上传归档资料")
async def upload_archive_document(request: DocumentUploadRequest):
    """
    上传归档资料
    
    - **order_id**: 订单ID
    - **document_type**: 资料类型（见枚举）
    - **file_name**: 文件名
    - **file_url**: 文件URL或本地路径
    - **uploaded_by**: 上传人
    
    自动识别document_type并更新清单中对应项为"已上传"
    """
    result = upload_document(
        order_id=request.order_id,
        document_type=request.document_type.value,
        file_name=request.file_name,
        file_url=request.file_url,
        uploaded_by=request.uploaded_by
    )
    
    if not result["success"]:
        return ApiResponse(code=400, message=result["message"], data=None)
    
    return ApiResponse(code=200, message=result["message"], data=result["data"])


# ==================== 归档状态查询 ====================

@router.get("/documents/{order_id}", response_model=ApiResponse, summary="获取订单所有资料")
async def get_order_documents(order_id: str):
    """
    获取某订单所有已上传资料
    
    - **order_id**: 订单ID
    
    返回该订单所有上传过的资料列表，按document_type分组
    """
    result = get_documents_by_order(order_id)
    return ApiResponse(code=200, message=result["message"], data=result["data"])


@router.get("/documents/detail/{document_id}", response_model=ApiResponse, summary="获取资料详情")
async def get_document_by_id(document_id: str):
    """
    获取资料详情
    
    - **document_id**: 资料ID
    
    返回资料的详细信息，包括OCR识别结果
    """
    result = get_document_detail(document_id)
    
    if not result["success"]:
        return ApiResponse(code=404, message=result["message"], data=None)
    
    return ApiResponse(code=200, message=result["message"], data=result["data"])


# ==================== OCR模拟接口 ====================

@router.post("/documents/{document_id}/ocr", response_model=ApiResponse, summary="OCR识别")
async def ocr_document(document_id: str):
    """
    模拟OCR识别
    
    - **document_id**: 资料ID
    
    根据document_type返回模拟的OCR结果，并存储到数据库
    
    示例返回：
    - id_card_front: {"name": "张三", "id_number": "110101199001011234", ...}
    - driving_license: {"plate_number": "京A12345", "brand": "宝马", ...}
    - vehicle_certificate: {"vin": "LSV123456789", "mortgage_status": "已抵押", ...}
    """
    result = process_ocr(document_id)
    
    if not result["success"]:
        return ApiResponse(code=400, message=result["message"], data=None)
    
    return ApiResponse(code=200, message=result["message"], data=result["data"])


# ==================== 归档进度统计 ====================

@router.get("/stats", response_model=ApiResponse, summary="归档统计")
async def get_stats():
    """
    归档统计
    
    返回：
    - total_orders: 需要归档的订单总数
    - complete_count: 已完成归档数
    - partial_count: 部分上传数
    - pending_count: 待上传数
    - complete_rate: 归档完成率
    - missing_documents: 缺失最多的资料类型TOP3
    """
    result = get_archive_stats()
    return ApiResponse(code=200, message=result["message"], data=result["data"])


# ==================== 资料类型枚举查询 ====================

@router.get("/document-types", response_model=ApiResponse, summary="获取资料类型列表")
async def get_document_types():
    """
    获取所有资料类型枚举
    
    返回资料类型代码、名称、是否必填等信息
    """
    from models import DOCUMENT_TYPE_CONFIG
    
    types = []
    for doc_type, config in DOCUMENT_TYPE_CONFIG.items():
        types.append({
            "type": doc_type,
            "name": config["name"],
            "required": config["required"]
        })
    
    return ApiResponse(
        code=200,
        message="success",
        data={"document_types": types}
    )
