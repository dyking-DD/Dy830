#!/usr/bin/env python3
"""
GPS管理模块 API 测试脚本
测试所有API接口
"""
import requests
import json
import random
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8001"


def print_response(name, response):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"📌 {name}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    except:
        print(f"响应: {response.text}")
        return None


def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    return print_response("健康检查", response)


def test_root():
    """测试根路由"""
    response = requests.get(f"{BASE_URL}/")
    return print_response("根路由", response)


def test_create_order():
    """测试创建订单"""
    data = {
        "customer_name": f"测试客户{random.randint(1000, 9999)}",
        "customer_phone": f"138{random.randint(10000000, 99999999)}",
        "car_model": "丰田凯美瑞 2024款"
    }
    response = requests.post(f"{BASE_URL}/api/v1/orders", params=data)
    result = print_response("创建测试订单", response)
    return result.get("data", {}).get("order", {}).get("id") if result else None


def test_list_orders():
    """测试订单列表"""
    response = requests.get(f"{BASE_URL}/api/v1/orders")
    return print_response("订单列表", response)


def test_register_gps_device(order_id):
    """测试注册GPS设备"""
    data = {
        "order_id": order_id,
        "imei": f"8675840300{random.randint(10000, 99999)}",
        "device_type": "wired",
        "install_location": "仪表盘下方",
        "install_staff": "李师傅"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/gps/devices",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    result = print_response("注册GPS设备", response)
    return result.get("data", {}).get("device", {}).get("device_id") if result else None


def test_list_devices():
    """测试设备列表"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/devices")
    return print_response("设备列表", response)


def test_get_device_detail(device_id):
    """测试设备详情"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/devices/{device_id}")
    return print_response("设备详情", response)


def test_get_device_location(device_id):
    """测试设备位置"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/devices/{device_id}/location")
    return print_response("设备位置", response)


def test_device_heartbeat(device_id):
    """测试设备心跳"""
    data = {
        "latitude": round(31.0 + random.random(), 6),
        "longitude": round(121.0 + random.random(), 6),
        "address": "上海市浦东新区测试地址"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/gps/devices/{device_id}/heartbeat",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    return print_response("设备心跳", response)


def test_mark_offline(device_id):
    """测试标记离线"""
    response = requests.post(f"{BASE_URL}/api/v1/gps/devices/{device_id}/offline")
    return print_response("标记设备离线", response)


def test_create_alert(device_id):
    """测试创建告警"""
    alert_types = ["overspeed", "out_of_zone", "power_off", "tamper", "low_battery", "sos"]
    data = {
        "device_id": device_id,
        "alert_type": random.choice(alert_types),
        "latitude": round(31.0 + random.random(), 6),
        "longitude": round(121.0 + random.random(), 6),
        "address": "告警测试位置"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/gps/alerts",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    result = print_response("创建告警", response)
    return result.get("data", {}).get("alert", {}).get("alert_id") if result else None


def test_list_alerts():
    """测试告警列表"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/alerts")
    return print_response("告警列表", response)


def test_handle_alert(alert_id):
    """测试处理告警"""
    data = {
        "handled_by": "测试管理员",
        "handle_note": "已处理，测试通过"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/gps/alerts/{alert_id}/handle",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    return print_response("处理告警", response)


def test_dashboard():
    """测试驾驶舱"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/dashboard")
    return print_response("GPS驾驶舱", response)


def test_poll():
    """测试轮询"""
    response = requests.get(f"{BASE_URL}/api/v1/gps/poll")
    return print_response("GPS轮询模拟", response)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 开始GPS管理模块API测试")
    print("="*60)
    
    # 基础测试
    test_health()
    test_root()
    
    # 创建订单
    order_id = test_create_order()
    
    if not order_id:
        print("\n❌ 创建订单失败，使用订单ID=1继续测试")
        order_id = 1
    
    # 订单列表
    test_list_orders()
    
    # 注册GPS设备
    device_id = test_register_gps_device(order_id)
    
    if not device_id:
        print("\n❌ 注册设备失败，尝试获取已有设备...")
        result = test_list_devices()
        if result and result.get("data", {}).get("devices"):
            device_id = result["data"]["devices"][0]["device_id"]
            print(f"使用设备: {device_id}")
        else:
            print("❌ 没有可用设备，部分测试跳过")
            return
    
    # 设备相关测试
    test_list_devices()
    test_get_device_detail(device_id)
    test_get_device_location(device_id)
    test_device_heartbeat(device_id)
    
    # 告警相关测试
    alert_id = test_create_alert(device_id)
    test_list_alerts()
    
    if alert_id:
        test_handle_alert(alert_id)
    
    # 驾驶舱和轮询
    test_dashboard()
    test_poll()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    # 检查服务是否运行
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
    except:
        print(f"❌ 无法连接到服务: {BASE_URL}")
        print("请先启动服务: python3 main.py 或 ./start.sh")
        sys.exit(1)
    
    # 运行测试
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "health":
            test_health()
        elif test_name == "order":
            test_create_order()
        elif test_name == "device":
            test_list_devices()
        elif test_name == "alert":
            test_list_alerts()
        elif test_name == "dashboard":
            test_dashboard()
        elif test_name == "poll":
            test_poll()
        else:
            print(f"未知测试: {test_name}")
    else:
        run_all_tests()
