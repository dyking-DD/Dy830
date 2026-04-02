"""
API使用示例 - 完整业务流程演示
"""
import sys
import os
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from service import OrderService, RepaymentService, MortgageService

def print_json(data):
    """格式化输出JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def demo_complete_workflow():
    """演示完整的业务流程"""
    print("=" * 80)
    print("📋 汽车分期管理平台 - 完整业务流程演示")
    print("=" * 80)
    
    # ==================== 第一步：创建订单 ====================
    print("\n🔹 第一步：创建订单")
    print("-" * 80)
    
    order_data = {
        "customer_name": "李四",
        "customer_phone": "13900139000",
        "customer_id_number": "110101199001011234",
        "car_brand": "奔驰",
        "car_model": "E300L",
        "car_vin": "WDDZF4KB5JA123456",
        "car_plate_number": "京B88888",
        "car_price": 450000.0,
        "loan_amount": 280000.0,
        "down_payment": 170000.0,
        "loan_period": 36,
        "monthly_payment": 8500.0,
        "interest_rate": 5.0,
        "bank_name": "工商银行",
        "created_by": "业务员张三"
    }
    
    order_result = OrderService.create_order(order_data)
    order_id = order_result["order_id"]
    
    print(f"✅ 订单创建成功")
    print_json(order_result)
    
    # ==================== 第二步：订单阶段流转 ====================
    print("\n🔹 第二步：订单阶段流转（垫资流程）")
    print("-" * 80)
    
    stages = [
        ("垫资预审", "客户资料齐全，进入垫资预审"),
        ("垫资审批中", "垫资审批中"),
        ("垫资通过", "垫资审批通过"),
        ("垫资已出账", "垫资已出账，金额28万"),
        ("垫资已还清", "垫资已还清"),
    ]
    
    for stage, remark in stages:
        result = OrderService.update_order_stage(order_id, stage, remark)
        print(f"  ✅ {result['old_stage']} → {result['new_stage']}")
    
    # ==================== 第三步：银行审批 ====================
    print("\n🔹 第三步：银行审批")
    print("-" * 80)
    
    stages = [
        ("银行审批中", "提交银行审批"),
        ("审批通过", "银行审批通过"),
        ("放款通知", "银行放款通知"),
    ]
    
    for stage, remark in stages:
        result = OrderService.update_order_stage(order_id, stage, remark)
        print(f"  ✅ {result['old_stage']} → {result['new_stage']}")
    
    # ==================== 第四步：提车与GPS ====================
    print("\n🔹 第四步：提车与GPS安装")
    print("-" * 80)
    
    stages = [
        ("待提车", "等待客户提车"),
        ("已提车", "客户已提车"),
        ("GPS安装中", "GPS安装中"),
        ("GPS已在线", "GPS已上线"),
    ]
    
    for stage, remark in stages:
        result = OrderService.update_order_stage(order_id, stage, remark)
        print(f"  ✅ {result['old_stage']} → {result['new_stage']}")
    
    # ==================== 第五步：归档与抵押 ====================
    print("\n🔹 第五步：资料归档与抵押登记")
    print("-" * 80)
    
    stages = [
        ("资料归档中", "资料归档中"),
        ("归档完成", "资料归档完成"),
        ("抵押登记中", "抵押登记中"),
        ("已抵押", "抵押登记完成"),
        ("正常还款中", "进入正常还款期"),
    ]
    
    for stage, remark in stages:
        result = OrderService.update_order_stage(order_id, stage, remark)
        print(f"  ✅ {result['old_stage']} → {result['new_stage']}")
    
    # ==================== 第六步：生成还款计划 ====================
    print("\n🔹 第六步：生成还款计划")
    print("-" * 80)
    
    plan_result = RepaymentService.generate_repayment_plans(
        order_id=order_id,
        loan_amount=280000.0,
        loan_period=36,
        start_date="2024-03-15",
        monthly_payment=8500.0
    )
    
    print(f"✅ 生成还款计划成功，共 {len(plan_result['plans'])} 期")
    print(f"客户姓名：{plan_result['customer_name']}")
    print(f"\n前3期还款计划：")
    for plan in plan_result['plans'][:3]:
        print(f"  第{plan['period_number']}期：{plan['due_date']}，应还 ¥{plan['due_amount']:.2f}")
    
    # ==================== 第七步：录入还款记录 ====================
    print("\n🔹 第七步：录入还款记录（前3期）")
    print("-" * 80)
    
    for i, plan in enumerate(plan_result['plans'][:3], 1):
        record_data = {
            "plan_id": plan['plan_id'],
            "actual_amount": 8500.0,
            "repayment_date": plan['due_date'],
            "payment_method": "银行转账",
            "remark": f"第{i}期还款"
        }
        
        result = RepaymentService.create_repayment_record(record_data)
        print(f"  ✅ 第{i}期还款成功，逾期天数：{result['overdue_days']}")
    
    # ==================== 第八步：查询还款统计 ====================
    print("\n🔹 第八步：查询还款统计")
    print("-" * 80)
    
    stats = RepaymentService.get_repayment_stats()
    print_json(stats)
    
    # ==================== 第九步：创建抵押登记 ====================
    print("\n🔹 第九步：创建抵押登记")
    print("-" * 80)
    
    mortgage_data = {
        "order_id": order_id,
        "mortgage_bank": "工商银行",
        "register_date": "2024-01-20",
        "expire_date": "2027-01-20",
        "certificate_number": "BJ2024001234"
    }
    
    mortgage_result = MortgageService.create_mortgage(mortgage_data)
    print(f"✅ 抵押登记成功")
    print_json(mortgage_result)
    
    # ==================== 第十步：查询订单详情 ====================
    print("\n🔹 第十步：查询订单完整信息")
    print("-" * 80)
    
    order_detail = OrderService.get_order_detail(order_id)
    print(f"订单ID：{order_detail['order_id']}")
    print(f"客户姓名：{order_detail['customer_name']}")
    print(f"车辆信息：{order_detail['car_brand']} {order_detail['car_model']}")
    print(f"贷款金额：¥{order_detail['loan_amount']:,.2f}")
    print(f"当前阶段：{order_detail['stage']}")
    print(f"创建时间：{order_detail['created_at']}")
    
    # ==================== 第十一步：查询驾驶舱 ====================
    print("\n🔹 第十一步：查询驾驶舱数据")
    print("-" * 80)
    
    from service import DashboardService
    dashboard = DashboardService.get_dashboard()
    
    print("📊 订单统计：")
    print_json(dashboard['orders_stats'])
    
    print("\n📊 还款统计：")
    print_json(dashboard['repayment_stats'])
    
    print("\n📊 抵押统计：")
    print_json(dashboard['mortgage_stats'])
    
    print("\n" + "=" * 80)
    print("✅ 完整业务流程演示完成！")
    print("=" * 80)

if __name__ == "__main__":
    demo_complete_workflow()
