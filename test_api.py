# -*- coding: utf-8 -*-
"""
API测试脚本
测试权限控制功能
"""
import requests
import json

BASE_URL = "http://localhost:8899"

def test_admin_login():
    """测试管理员登录"""
    print("\n🔐 测试管理员登录...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result.get("data", {}).get("token")

def test_customer_login():
    """测试客户登录"""
    print("\n🔐 测试客户登录...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/customer/login", json={
        "phone": "13800138001",
        "password": "123456"
    })
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result.get("data", {}).get("token")

def test_get_orders_admin(token):
    """测试管理员获取订单列表"""
    print("\n📦 测试管理员获取订单列表...")
    response = requests.get(
        f"{BASE_URL}/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"订单数量: {result.get('data', {}).get('total', 0)}")

def test_get_orders_customer(token):
    """测试客户获取自己的订单"""
    print("\n📦 测试客户获取自己的订单...")
    response = requests.get(
        f"{BASE_URL}/api/v1/customer/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"订单数量: {len(result.get('data', []))}")
    else:
        print(f"错误信息: {result.get('message')}")

def test_unauthorized_access():
    """测试未授权访问"""
    print("\n🔒 测试未授权访问...")
    response = requests.get(f"{BASE_URL}/api/v1/orders")
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"错误信息: {result.get('detail', result.get('message'))}")

if __name__ == "__main__":
    print("="*60)
    print("🧪 API测试脚本")
    print("="*60)
    print("\n⚠️  请先启动服务: python3 main.py")
    print("="*60)
    
    try:
        # 测试管理员登录
        admin_token = test_admin_login()
        
        # 测试客户登录
        customer_token = test_customer_login()
        
        if admin_token:
            # 测试管理员访问订单
            test_get_orders_admin(admin_token)
        
        if customer_token:
            # 测试客户访问自己的订单
            test_get_orders_customer(customer_token)
        
        # 测试未授权访问
        test_unauthorized_access()
        
        print("\n" + "="*60)
        print("✅ 所有API测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print("请确保服务已启动: python3 main.py")
