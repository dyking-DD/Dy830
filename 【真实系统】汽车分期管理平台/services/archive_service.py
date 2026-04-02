# -*- coding: utf-8 -*-
"""
归档服务模块
处理归档清单管理、资料上传、OCR识别等业务逻辑
"""
import json
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, generate_id
from models import DOCUMENT_TYPE_CONFIG, REQUIRED_DOCUMENTS


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


# ==================== 归档清单服务 ====================

def init_checklist(order_id: str) -> dict:
    """初始化归档清单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        if cursor.fetchone():
            return {"success": False, "message": "归档清单已存在"}
        
        # 获取订单客户信息
        cursor.execute("""
            SELECT o.order_id, c.name as customer_name
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_id = ?
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            return {"success": False, "message": "订单不存在"}
        
        # 创建清单
        checklist_id = generate_id("CL")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO archive_checklists (checklist_id, order_id, overall_status, created_at, updated_at)
            VALUES (?, ?, '待上传', ?, ?)
        """, (checklist_id, order_id, now, now))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "归档清单初始化成功",
            "data": {"checklist_id": checklist_id, "order_id": order_id}
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"初始化失败: {str(e)}"}
    finally:
        conn.close()


def get_checklist(order_id: str) -> dict:
    """获取订单归档清单状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询归档清单
        cursor.execute("""
            SELECT ac.*, c.name as customer_name
            FROM archive_checklists ac
            LEFT JOIN orders o ON ac.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE ac.order_id = ?
        """, (order_id,))
        
        checklist = cursor.fetchone()
        if not checklist:
            return {"success": False, "message": "归档清单不存在"}
        
        checklist_dict = row_to_dict(checklist)
        
        # 构建清单项列表
        items = []
        required_uploaded = 0
        
        for doc_type, config in DOCUMENT_TYPE_CONFIG.items():
            status_value = checklist_dict.get(doc_type, 0)
            is_uploaded = status_value == 1
            status = "已上传" if is_uploaded else "待上传"
            
            items.append({
                "type": doc_type,
                "name": config["name"],
                "required": config["required"],
                "status": status
            })
            
            if is_uploaded and config["required"]:
                required_uploaded += 1
        
        # 计算完成进度
        progress_percent = int((required_uploaded / len(REQUIRED_DOCUMENTS)) * 100)
        
        result = {
            "order_id": order_id,
            "customer_name": checklist_dict.get("customer_name"),
            "overall_status": checklist_dict.get("overall_status"),
            "progress_percent": progress_percent,
            "items": items
        }
        
        return {"success": True, "data": result}
    finally:
        conn.close()


def upload_document(data: dict) -> dict:
    """上传归档资料"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        order_id = data.get("order_id")
        document_type = data.get("document_type")
        
        # 检查归档清单是否存在，不存在则初始化
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        if not cursor.fetchone():
            init_checklist(order_id)
        
        # 创建资料记录
        document_id = generate_id("DOC")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO archive_documents (
                document_id, order_id, document_type, file_name, file_url, upload_time, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id, order_id, document_type,
            data.get("file_name"), data.get("file_url"), now, data.get("uploaded_by")
        ))
        
        # 更新清单中该项为已上传
        cursor.execute(f"""
            UPDATE archive_checklists SET {document_type} = 1, updated_at = ?
            WHERE order_id = ?
        """, (now, order_id))
        
        # 更新整体状态
        cursor.execute("SELECT * FROM archive_checklists WHERE order_id = ?", (order_id,))
        checklist = cursor.fetchone()
        checklist_dict = row_to_dict(checklist)
        
        required_uploaded = sum(1 for doc in REQUIRED_DOCUMENTS if checklist_dict.get(doc, 0) == 1)
        
        if required_uploaded == len(REQUIRED_DOCUMENTS):
            new_status = "已完整"
        elif required_uploaded > 0:
            new_status = "部分上传"
        else:
            new_status = "待上传"
        
        cursor.execute("""
            UPDATE archive_checklists SET overall_status = ?, updated_at = ?
            WHERE order_id = ?
        """, (new_status, now, order_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "资料上传成功",
            "data": {
                "document_id": document_id,
                "overall_status": new_status,
                "progress": f"{required_uploaded}/{len(REQUIRED_DOCUMENTS)}"
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"上传失败: {str(e)}"}
    finally:
        conn.close()


def ocr_document(document_id: str) -> dict:
    """OCR识别资料（模拟）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询资料
        cursor.execute("SELECT * FROM archive_documents WHERE document_id = ?", (document_id,))
        document = cursor.fetchone()
        
        if not document:
            return {"success": False, "message": "资料不存在"}
        
        doc_dict = row_to_dict(document)
        document_type = doc_dict["document_type"]
        
        # 生成模拟OCR结果
        mock_results = {
            "id_card_front": {
                "name": "张三",
                "gender": "男",
                "nation": "汉",
                "birth_date": "1990年01月01日",
                "id_number": "110101199001011234",
                "address": "北京市朝阳区XX路XX号"
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
                "vin": "LBV12345678901234"
            },
            "vehicle_certificate": {
                "vin": "LSV12345678901234",
                "engine_number": "EA888123456",
                "brand": "大众/Volkswagen",
                "mortgage_status": "已抵押"
            }
        }
        
        ocr_result = mock_results.get(document_type, {"message": "无OCR结果"})
        ocr_json = json.dumps(ocr_result, ensure_ascii=False)
        
        # 更新数据库
        cursor.execute("""
            UPDATE archive_documents SET ocr_result = ?
            WHERE document_id = ?
        """, (ocr_json, document_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "OCR识别成功",
            "data": {
                "document_id": document_id,
                "document_type": document_type,
                "type_name": DOCUMENT_TYPE_CONFIG.get(document_type, {}).get("name", document_type),
                "ocr_result": ocr_result
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"OCR识别失败: {str(e)}"}
    finally:
        conn.close()


def get_documents_by_order(order_id: str) -> dict:
    """获取订单所有已上传资料"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM archive_documents
            WHERE order_id = ?
            ORDER BY document_type, upload_time DESC
        """, (order_id,))
        
        documents = cursor.fetchall()
        
        # 按类型分组
        grouped = {}
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
        
        return {
            "success": True,
            "data": {
                "order_id": order_id,
                "total_count": len(documents),
                "grouped_documents": grouped_documents
            }
        }
    finally:
        conn.close()


def get_stats() -> dict:
    """获取归档统计"""
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
        
        missing_stats.sort(key=lambda x: x["missing_count"], reverse=True)
        top3_missing = missing_stats[:3]
        
        return {
            "success": True,
            "data": {
                "total_orders": total,
                "complete_count": complete_count,
                "partial_count": stats["partial_count"] or 0,
                "pending_count": stats["pending_count"] or 0,
                "complete_rate": complete_rate,
                "missing_documents": top3_missing
            }
        }
    finally:
        conn.close()
