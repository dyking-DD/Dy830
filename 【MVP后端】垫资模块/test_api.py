#!/usr/bin/env python3
"""
快速测试脚本
用于验证垫资管理模块 API 是否正常工作
"""
import requests
import json
from datetime import date, timedelta

# API 基础 URL
BASE_URL = "http://localhost:8000"

def test_api():
    """测试 API 接口"""
    
    print("=" * 60)
    print("🧪 垫资管理模块 API 测试")
    print("=" * 60)
    
    # 1. 健康检查
    print("\n1️⃣  健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   ✅ 服务状态: {response.json()['status']}")
    except Exception as e:
        print(f"   ❌ 服务未启动，请先运行: python main.py")
        return
    
    # 2. 创建订单
    print("\n2️⃣  创建测试订单...")
    order_data = {
        "customer_name": "测试客户",
        "customer_phone": "13800138000",
        "car_model": "测试车型",
        "car_price": 200000.00,
        "down_payment": 60000.00,
        "loan_amount": 140000.00
    }
    response = requests.post(f"{BASE_URL}/api/v1/orders", json=order_data)
    order = response.json()
    print(f"   ✅ 订单创建成功: {order['data']['order']['order_no']}")
    order_id = order['data']['order']['id']
    
    # 3. 创建垫资单
    print("\n3️⃣  创建垫资单...")
    advance_data = {
        "order_id": order_id,
        "customer_name": "测试客户",
        "amount": 50000.00,
        "lender_type": "company",
        "lender_account": "测试账户",
        "purpose": "首付垫资",
        "interest_rate_type": "monthly",
        "monthly_rate": 0.015,
        "start_date": str(date.today()),
        "expected_repay_date": str(date.today() + timedelta(days=30))
    }
    response = requests.post(f"{BASE_URL}/api/v1/advances", json=advance_data)
    advance = response.json()
    print(f"   ✅ 垫资单创建成功: {advance['data']['advance']['advance_no']}")
    advance_id = advance['data']['advance']['id']
    
    # 4. 审批垫资单
    print("\n4️⃣  审批垫资单...")
    approval_data = {
        "approver": "测试经理",
        "approval_opinion": "同意垫资",
        "approved": True
    }
    response = requests.post(f"{BASE_URL}/api/v1/advances/{advance_id}/approve", json=approval_data)
    print(f"   ✅ 审批成功，状态: {response.json()['data']['advance']['status']}")
    
    # 5. 垫资出账
    print("\n5️⃣  垫资出账...")
    disburse_data = {}
    response = requests.post(f"{BASE_URL}/api/v1/advances/{advance_id}/disburse", json=disburse_data)
    print(f"   ✅ 出账成功，状态: {response.json()['data']['advance']['status']}")
    
    # 6. 查询垫资单列表
    print("\n6️⃣  查询垫资单列表...")
    response = requests.get(f"{BASE_URL}/api/v1/advances")
    result = response.json()
    print(f"   ✅ 查询成功，共 {result['data']['total']} 条记录")
    
    # 7. 查询垫资仪表盘
    print("\n7️⃣  查询垫资仪表盘...")
    response = requests.get(f"{BASE_URL}/api/v1/advances/dashboard")
    dashboard = response.json()['data']
    print(f"   ✅ 当前垫资余额: ¥{dashboard['current_balance']:,.2f}")
    print(f"   ✅ 待还笔数: {dashboard['pending_repay_count']} 笔")
    
    # 8. 垫资还款
    print("\n8️⃣  垫资还款...")
    repay_data = {
        "actual_repay_amount": 50750.00  # 本金 + 预估利息
    }
    response = requests.post(f"{BASE_URL}/api/v1/advances/{advance_id}/repay", json=repay_data)
    result = response.json()
    print(f"   ✅ 还款成功")
    print(f"   📊 实际天数: {result['data']['advance']['actual_days']} 天")
    print(f"   💰 计算利息: ¥{result['data']['advance']['calculated_interest']:,.2f}")
    
    # 9. 检查逾期
    print("\n9️⃣  检查逾期垫资单...")
    response = requests.post(f"{BASE_URL}/api/v1/advances/check-overdue")
    result = response.json()
    print(f"   ✅ 检查完成: {result['message']}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print("\n📖 访问 API 文档: http://localhost:8000/docs")


if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器，请先启动 API 服务:")
        print("   python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
