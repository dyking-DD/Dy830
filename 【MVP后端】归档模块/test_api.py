"""
API测试脚本
用于测试归档模块所有API接口
"""
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8001/api/v1/archive"


def print_response(name: str, response: requests.Response):
    """打印响应结果"""
    print(f"\n{'='*50}")
    print(f"【{name}】")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except:
        print(f"响应: {response.text}")
    print('='*50)


def test_all_apis():
    """测试所有API接口"""
    
    print("\n" + "🚀 开始测试归档模块API" + "\n")
    
    # 测试用的订单ID
    test_order_id = "FP-20260402-0001"
    test_document_id = None
    
    # ==================== 1. 获取资料类型列表 ====================
    print("\n📋 步骤1: 获取资料类型列表")
    response = requests.get(f"{BASE_URL}/document-types")
    print_response("获取资料类型列表", response)
    
    # ==================== 2. 初始化归档清单 ====================
    print("\n📋 步骤2: 初始化归档清单")
    response = requests.post(
        f"{BASE_URL}/checklists",
        json={"order_id": test_order_id}
    )
    print_response("初始化归档清单", response)
    
    # ==================== 3. 获取归档清单状态 ====================
    print("\n📋 步骤3: 获取归档清单状态（初始）")
    response = requests.get(f"{BASE_URL}/checklists/{test_order_id}")
    print_response("获取归档清单状态", response)
    
    # ==================== 4. 上传资料 - 身份证人像面 ====================
    print("\n📄 步骤4: 上传身份证人像面")
    response = requests.post(
        f"{BASE_URL}/documents",
        json={
            "order_id": test_order_id,
            "document_type": "id_card_front",
            "file_name": "张三_身份证人像面.jpg",
            "file_url": "/uploads/2024/04/张三_身份证人像面.jpg",
            "uploaded_by": "业务员A"
        }
    )
    print_response("上传身份证人像面", response)
    if response.status_code == 200:
        test_document_id = response.json().get("data", {}).get("document_id")
    
    # ==================== 5. 上传资料 - 行驶证 ====================
    print("\n📄 步骤5: 上传行驶证")
    response = requests.post(
        f"{BASE_URL}/documents",
        json={
            "order_id": test_order_id,
            "document_type": "driving_license",
            "file_name": "张三_行驶证.jpg",
            "file_url": "/uploads/2024/04/张三_行驶证.jpg",
            "uploaded_by": "业务员A"
        }
    )
    print_response("上传行驶证", response)
    
    # ==================== 6. 上传资料 - GPS安装照片 ====================
    print("\n📄 步骤6: 上传GPS安装照片")
    response = requests.post(
        f"{BASE_URL}/documents",
        json={
            "order_id": test_order_id,
            "document_type": "gps_photos",
            "file_name": "GPS安装照片.zip",
            "file_url": "/uploads/2024/04/GPS安装照片.zip",
            "uploaded_by": "业务员A"
        }
    )
    print_response("上传GPS安装照片", response)
    
    # ==================== 7. 再次获取归档清单状态 ====================
    print("\n📋 步骤7: 获取归档清单状态（部分上传）")
    response = requests.get(f"{BASE_URL}/checklists/{test_order_id}")
    print_response("获取归档清单状态", response)
    
    # ==================== 8. 获取订单所有资料 ====================
    print("\n📄 步骤8: 获取订单所有已上传资料")
    response = requests.get(f"{BASE_URL}/documents/{test_order_id}")
    print_response("获取订单所有资料", response)
    
    # ==================== 9. 获取资料详情 ====================
    if test_document_id:
        print("\n📄 步骤9: 获取资料详情")
        response = requests.get(f"{BASE_URL}/documents/detail/{test_document_id}")
        print_response("获取资料详情", response)
    
    # ==================== 10. OCR识别 ====================
    if test_document_id:
        print("\n🔍 步骤10: OCR识别（身份证人像面）")
        response = requests.post(f"{BASE_URL}/documents/{test_document_id}/ocr")
        print_response("OCR识别", response)
    
    # ==================== 11. 再次获取资料详情（含OCR结果） ====================
    if test_document_id:
        print("\n📄 步骤11: 获取资料详情（含OCR结果）")
        response = requests.get(f"{BASE_URL}/documents/detail/{test_document_id}")
        print_response("获取资料详情（含OCR）", response)
    
    # ==================== 12. 归档统计 ====================
    print("\n📊 步骤12: 归档统计")
    response = requests.get(f"{BASE_URL}/stats")
    print_response("归档统计", response)
    
    print("\n✅ 所有API测试完成！\n")


def test_complete_archive():
    """测试完整归档流程"""
    
    print("\n" + "🎯 测试完整归档流程" + "\n")
    
    test_order_id = "FP-20260402-0002"
    
    # 上传所有必填资料
    required_docs = [
        ("id_card_front", "身份证人像面.jpg"),
        ("id_card_back", "身份证国徽面.jpg"),
        ("driving_license", "行驶证.jpg"),
        ("vehicle_certificate", "车辆登记证.jpg"),
        ("gps_photos", "GPS安装照片.zip"),
        ("pickup_confirmation", "提车确认单.pdf"),
        ("advance_agreement", "垫资协议.pdf"),
    ]
    
    # 初始化清单
    print("📋 初始化归档清单...")
    requests.post(f"{BASE_URL}/checklists", json={"order_id": test_order_id})
    
    # 逐个上传
    for i, (doc_type, file_name) in enumerate(required_docs):
        print(f"📄 上传 [{i+1}/{len(required_docs)}]: {doc_type}")
        requests.post(
            f"{BASE_URL}/documents",
            json={
                "order_id": test_order_id,
                "document_type": doc_type,
                "file_name": file_name,
                "file_url": f"/uploads/2024/04/{file_name}",
                "uploaded_by": "业务员A"
            }
        )
    
    # 获取最终状态
    print("\n📋 最终归档清单状态:")
    response = requests.get(f"{BASE_URL}/checklists/{test_order_id}")
    data = response.json()
    print(f"整体状态: {data['data']['overall_status']}")
    print(f"完成进度: {data['data']['progress_percent']}%")
    
    print("\n✅ 完整归档流程测试完成！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("汽车分期管理平台 - 资料归档模块 API 测试")
    print("=" * 60)
    print("\n请确保服务已启动: python main.py")
    print("服务地址: http://localhost:8001")
    print("\n按回车键开始测试...")
    input()
    
    try:
        # 测试所有API
        test_all_apis()
        
        # 测试完整归档流程
        test_complete_archive()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务，请确保服务已启动！")
        print("启动命令: python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
