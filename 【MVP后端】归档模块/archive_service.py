"""
归档服务层 - 业务逻辑处理
包含归档清单管理、资料上传、OCR模拟等功能
"""
import json
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from database import get_db_connection
from models import (
    DOCUMENT_TYPE_CONFIG, REQUIRED_DOCUMENTS,
    OverallStatus, UploadStatus
)


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


def generate_id(prefix: str) -> str:
    """生成唯一ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_num = random.randint(1000, 9999)
    return f"{prefix}-{timestamp}-{random_num}"


# ==================== 归档清单服务 ====================

def init_checklist(order_id: str, customer_name: str = None) -> dict:
    """初始化归档清单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        existing = cursor.fetchone()
        
        if existing:
            return {
                "success": False,
                "message": f"订单 {order_id} 的归档清单已存在",
                "data": row_to_dict(existing)
            }
        
        checklist_id = generate_id("CL")
        current_time = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO archive_checklists 
            (checklist_id, order_id, customer_name, overall_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (checklist_id, order_id, customer_name, OverallStatus.PENDING.value, current_time, current_time))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM archive_checklists WHERE checklist_id = ?", (checklist_id,))
        checklist = cursor.fetchone()
        
        return {
            "success": True,
            "message": "归档清单初始化成功",
            "data": row_to_dict(checklist)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"初始化失败: {str(e)}", "data": None}
    finally:
        conn.close()


def get_checklist(order_id: str) -> dict:
    """获取订单归档清单状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        checklist = cursor.fetchone()
        
        if not checklist:
            return {
                "success": False,
                "message": f"订单 {order_id} 的归档清单不存在",
                "data": None
            }
        
        checklist_dict = row_to_dict(checklist)
        
        items = []
        required_uploaded = 0
        
        for doc_type, config in DOCUMENT_TYPE_CONFIG.items():
            status_value = checklist_dict.get(doc_type, 0)
            is_uploaded = status_value == 1
            status = UploadStatus.UPLOADED.value if is_uploaded else UploadStatus.PENDING.value
            
            items.append({
                "type": doc_type,
                "name": config["name"],
                "required": config["required"],
                "status": status
            })
            
            if is_uploaded and config["required"]:
                required_uploaded += 1
        
        progress_percent = int((required_uploaded / len(REQUIRED_DOCUMENTS)) * 100)
        
        result = {
            "order_id": order_id,
            "customer_name": checklist_dict.get("customer_name"),
            "overall_status": checklist_dict.get("overall_status"),
            "progress_percent": progress_percent,
            "items": items
        }
        
        return {"success": True, "message": "success", "data": result}
    finally:
        conn.close()


def update_checklist_status(order_id: str, document_type: str) -> dict:
    """更新清单中某项的状态为已上传"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        current_time = datetime.now().isoformat()
        
        cursor.execute(f"""
            UPDATE archive_checklists
            SET {document_type} = 1, updated_at = ?
            WHERE order_id = ?
        """, (current_time, order_id))
        
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        checklist = cursor.fetchone()
        
        if not checklist:
            return {"success": False, "message": "清单不存在", "data": None}
        
        checklist_dict = row_to_dict(checklist)
        
        required_uploaded = sum(1 for doc in REQUIRED_DOCUMENTS if checklist_dict.get(doc, 0) == 1)
        
        if required_uploaded == len(REQUIRED_DOCUMENTS):
            new_status = OverallStatus.COMPLETE.value
        elif required_uploaded > 0:
            new_status = OverallStatus.PARTIAL.value
        else:
            new_status = OverallStatus.PENDING.value
        
        cursor.execute("""
            UPDATE archive_checklists
            SET overall_status = ?, updated_at = ?
            WHERE order_id = ?
        """, (new_status, current_time, order_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"清单状态已更新为 {new_status}",
            "data": {"overall_status": new_status}
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"更新失败: {str(e)}", "data": None}
    finally:
        conn.close()


# ==================== 资料上传服务 ====================

def upload_document(
    order_id: str,
    document_type: str,
    file_name: str,
    file_url: str,
    uploaded_by: str
) -> dict:
    """上传归档资料"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        checklist = cursor.fetchone()
        
        if not checklist:
            init_result = init_checklist(order_id)
            if not init_result["success"]:
                return init_result
        
        document_id = generate_id("DOC")
        current_time = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO archive_documents
            (document_id, order_id, document_type, file_name, file_url, upload_time, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (document_id, order_id, document_type, file_name, file_url, current_time, uploaded_by))
        
        conn.commit()
        
        update_checklist_status(order_id, document_type)
        
        cursor.execute("SELECT * FROM archive_documents WHERE document_id = ?", (document_id,))
        document = cursor.fetchone()
        
        return {
            "success": True,
            "message": "资料上传成功",
            "data": row_to_dict(document)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"上传失败: {str(e)}", "data": None}
    finally:
        conn.close()


def get_documents_by_order(order_id: str) -> dict:
    """获取某订单所有已上传资料，按类型分组"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM archive_documents
            WHERE order_id = ?
            ORDER BY document_type, upload_time DESC
        """, (order_id,))
        
        documents = cursor.fetchall()
        
        grouped: Dict[str, List] = {}
        for doc in documents:
            doc_dict = row_to_dict(doc)
            doc_type = doc_dict["document_type"]
            
            if doc_dict.get("ocr_result"):
                try:
                    doc_dict["ocr_result"] = json.loads(doc_dict["ocr_result"])
                except:
                    pass
            
            if doc_type not in grouped:
                grouped[doc_type] = []
            grouped[doc_type].append(doc_dict)
        
        grouped_documents = []
        for doc_type, docs in grouped.items():
            type_name = DOCUMENT_TYPE_CONFIG.get(doc_type, {}).get("name", doc_type)
            grouped_documents.append({
                "document_type": doc_type,
                "type_name": type_name,
                "documents": docs
            })
        
        result = {
            "order_id": order_id,
            "total_count": len(documents),
            "grouped_documents": grouped_documents
        }
        
        return {"success": True, "message": "success", "data": result}
    finally:
        conn.close()


def get_document_detail(document_id: str) -> dict:
    """获取资料详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM archive_documents WHERE document_id = ?", (document_id,))
        document = cursor.fetchone()
        
        if not document:
            return {
                "success": False,
                "message": f"资料 {document_id} 不存在",
                "data": None
            }
        
        doc_dict = row_to_dict(document)
        
        if doc_dict.get("ocr_result"):
            try:
                doc_dict["ocr_result"] = json.loads(doc_dict["ocr_result"])
            except:
                pass
        
        return {"success": True, "message": "success", "data": doc_dict}
    finally:
        conn.close()


# ==================== OCR模拟服务 ====================

def get_mock_ocr_result(document_type: str) -> dict:
    """根据资料类型生成模拟OCR结果"""
    mock_results = {
        "id_card_front": {
            "name": "张三",
            "gender": "男",
            "nation": "汉",
            "birth_date": "1990年01月01日",
            "id_number": "110101199001011234",
            "address": "北京市朝阳区XX路XX号XX小区XX号楼XX单元XX室"
        },
        "id_card_back": {
            "authority": "北京市公安局朝阳分局",
            "valid_period": "2020.01.01-2040.01.01"
        },
        "driving_license": {
            "plate_number": "京A12345",
            "vehicle_type": "小型轿车",
            "brand": "宝马/BMW 320Li",
            "owner": "张三",
            "address": "北京市朝阳区XX路XX号",
            "use_character": "非营运",
            "model": "BMW7201LM",
            "vin": "LBV12345678901234",
            "engine_number": "B48B20C123456",
            "register_date": "2023-06-15",
            "issue_date": "2023-06-15"
        },
        "vehicle_certificate": {
            "vin": "LSV12345678901234",
            "engine_number": "EA888123456",
            "brand": "大众/Volkswagen",
            "model": "帕萨特 330TSI",
            "owner": "张三",
            "register_date": "2024-03-20",
            "mortgage_status": "已抵押",
            "mortgagee": "XX汽车金融有限公司",
            "mortgage_date": "2024-03-25"
        },
        "gps_photos": {
            "device_id": "GPS-2024-0001234",
            "install_date": "2024-03-20",
            "install_location": "驾驶座下方",
            "installer": "李师傅",
            "photo_count": 3
        },
        "pickup_confirmation": {
            "customer_name": "张三",
            "pickup_date": "2024-03-20",
            "car_model": "宝马320Li",
            "plate_number": "京A12345",
            "confirmed_by": "销售顾问：王经理",
            "notes": "车辆已验收，无异议"
        },
        "advance_agreement": {
            "party_a": "XX汽车服务有限公司",
            "party_b": "张三",
            "amount": "50000.00",
            "rate": "月息1.5%",
            "start_date": "2024-03-20",
            "expected_repay_date": "2024-04-20",
            "sign_date": "2024-03-20"
        },
        "invoice": {
            "invoice_number": "No.12345678",
            "seller": "XX汽车销售有限公司",
            "buyer": "张三",
            "vehicle_model": "宝马320Li",
            "amount": "350000.00",
            "tax": "45500.00",
            "total": "395500.00",
            "date": "2024-03-18"
        },
        "insurance": {
            "policy_number": "PDAA20241234567890",
            "insurance_company": "中国人民财产保险股份有限公司",
            "insured": "张三",
            "plate_number": "京A12345",
            "insurance_type": "交强险+商业险",
            "premium": "8500.00",
            "effective_date": "2024-03-20",
            "expiry_date": "2025-03-19"
        }
    }
    
    return mock_results.get(document_type, {"message": "无OCR结果"})


def process_ocr(document_id: str) -> dict:
    """
    模拟OCR识别
    根据document_type返回模拟的OCR结果，并存储到数据库
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询资料
        cursor.execute("SELECT * FROM archive_documents WHERE document_id = ?", (document_id,))
        document = cursor.fetchone()
        
        if not document:
            return {
                "success": False,
                "message": f"资料 {document_id} 不存在",
                "data": None
            }
        
        doc_dict = row_to_dict(document)
        document_type = doc_dict["document_type"]
        
        # 获取模拟OCR结果
        ocr_result = get_mock_ocr_result(document_type)
        ocr_json = json.dumps(ocr_result, ensure_ascii=False)
        
        # 更新数据库
        cursor.execute("""
            UPDATE archive_documents
            SET ocr_result = ?
            WHERE document_id = ?
        """, (ocr_json, document_id))
        
        conn.commit()
        
        # 返回结果
        result = {
            "document_id": document_id,
            "document_type": document_type,
            "type_name": DOCUMENT_TYPE_CONFIG.get(document_type, {}).get("name", document_type),
            "ocr_result": ocr_result
        }
        
        return {
            "success": True,
            "message": "OCR识别成功",
            "data": result
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"OCR识别失败: {str(e)}", "data": None}
    finally:
        conn.close()


# ==================== 归档统计服务 ====================

def get_archive_stats() -> dict:
    """
    归档统计
    返回归档进度统计数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 统计各状态数量
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN overall_status = '已完整' THEN 1 ELSE 0 END) as complete_count,
                SUM(CASE WHEN overall_status = '部分上传' THEN 1 ELSE 0 END) as partial_count,
                SUM(CASE WHEN overall_status = '待上传' THEN 1 ELSE 0 END) as pending_count
            FROM archive_checklists
        """)
        
        stats = cursor.fetchone()
        
        total = stats["total"] or 0
        complete_count = stats["complete_count"] or 0
        partial_count = stats["partial_count"] or 0
        pending_count = stats["pending_count"] or 0
        
        # 计算完成率
        complete_rate = round((complete_count / total * 100), 2) if total > 0 else 0.0
        
        # 统计缺失最多的资料类型TOP3
        missing_stats = []
        for doc_type in REQUIRED_DOCUMENTS:
            cursor.execute(f"""
                SELECT COUNT(*) as missing_count
                FROM archive_checklists
                WHERE {doc_type} = 0
            """)
            missing_count = cursor.fetchone()["missing_count"]
            type_name = DOCUMENT_TYPE_CONFIG.get(doc_type, {}).get("name", doc_type)
            missing_stats.append({
                "type": doc_type,
                "name": type_name,
                "missing_count": missing_count
            })
        
        # 排序取TOP3
        missing_stats.sort(key=lambda x: x["missing_count"], reverse=True)
        top3_missing = missing_stats[:3]
        
        result = {
            "total_orders": total,
            "complete_count": complete_count,
            "partial_count": partial_count,
            "pending_count": pending_count,
            "complete_rate": complete_rate,
            "missing_documents": top3_missing
        }
        
        return {
            "success": True,
            "message": "success",
            "data": result
        }
    finally:
        conn.close()
