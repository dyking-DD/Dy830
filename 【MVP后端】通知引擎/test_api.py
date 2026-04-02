# -*- coding: utf-8 -*-
"""
通知引擎测试脚本
用于测试各个API接口
"""
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000/api/v1/notifications"


def print_response(title, response):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    print(f"响应内容:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print(f"{'='*60}\n")


def test_get_templates():
    """测试获取所有模板"""
    response = requests.get(f"{BASE_URL}/templates")
    print_response("获取所有模板", response)


def test_get_template_detail():
    """测试获取模板详情"""
    template_code = "order_created"
    response = requests.get(f"{BASE_URL}/templates/{template_code}")
    print_response(f"获取模板详情 - {template_code}", response)


def test_send_notification():
    """测试发送通知"""
    data = {
        "order_id": "ORD202401010001",
        "channel": "wechat",
        "recipient": "张三",
        "recipient_phone": "13800138000",
        "template_code": "order_created",
        "template_params": {"order_id": "ORD202401010001"},
        "content": "您已提交分期申请，单号ORD202401010001，我们将在24小时内联系您。"
    }
    response = requests.post(f"{BASE_URL}/send", json=data)
    print_response("发送通知", response)
    return response.json()["data"]["log_id"]


def test_trigger_notification():
    """测试业务节点触发通知"""
    data = {
        "stage": "bank_approved",
        "order_id": "ORD202401010002",
        "recipient": "李四",
        "recipient_phone": "13900139000",
        "channel": "sms",
        "template_params": {}
    }
    response = requests.post(f"{BASE_URL}/trigger", json=data)
    print_response("业务节点触发通知", response)


def test_batch_send():
    """测试批量发送"""
    data = {
        "notifications": [
            {
                "order_id": "ORD202401010003",
                "channel": "system",
                "recipient": "王五",
                "recipient_phone": "13700137000",
                "template_code": "advance_approved",
                "template_params": {"amount": "50000", "date": "2024-01-05"}
            },
            {
                "order_id": "ORD202401010004",
                "channel": "app_push",
                "recipient": "赵六",
                "recipient_phone": "13600136000",
                "template_code": "gps_online",
                "template_params": {"imei": "863254012345678"}
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/batch", json=data)
    print_response("批量发送通知", response)


def test_get_logs():
    """测试查询日志"""
    # 测试不带筛选条件
    response = requests.get(f"{BASE_URL}/logs?page=1&page_size=10")
    print_response("查询日志列表（全部）", response)
    
    # 测试按订单ID筛选
    response = requests.get(f"{BASE_URL}/logs?order_id=ORD202401010001&page=1&page_size=10")
    print_response("查询日志列表（按订单ID筛选）", response)
    
    # 测试按渠道筛选
    response = requests.get(f"{BASE_URL}/logs?channel=wechat&page=1&page_size=10")
    print_response("查询日志列表（按渠道筛选）", response)


def test_get_log_detail(log_id):
    """测试获取日志详情"""
    response = requests.get(f"{BASE_URL}/logs/{log_id}")
    print_response(f"获取日志详情 - {log_id}", response)


def test_get_stats():
    """测试获取统计数据"""
    response = requests.get(f"{BASE_URL}/stats")
    print_response("获取统计数据", response)


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🧪 开始测试通知引擎API")
    print("="*60 + "\n")
    
    try:
        # 1. 测试模板管理
        print("\n📌 测试模板管理功能")
        test_get_templates()
        test_get_template_detail()
        
        # 2. 测试发送通知
        print("\n📌 测试发送通知功能")
        log_id = test_send_notification()
        
        # 3. 测试业务节点触发
        print("\n📌 测试业务节点触发功能")
        test_trigger_notification()
        
        # 4. 测试批量发送
        print("\n📌 测试批量发送功能")
        test_batch_send()
        
        # 5. 测试日志查询
        print("\n📌 测试日志查询功能")
        test_get_logs()
        test_get_log_detail(log_id)
        
        # 6. 测试统计
        print("\n📌 测试统计功能")
        test_get_stats()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("请确保服务已启动: python main.py\n")
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}\n")


if __name__ == "__main__":
    main()
