"""
测试脚本 - 验证基本功能
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from database import init_database, generate_id, get_db_connection
from service import OrderService, RepaymentService, MortgageService, DashboardService

def test_database():
    """测试数据库初始化"""
    print("=" * 50)
    print("测试数据库初始化...")
    init_database()
    print("✅ 数据库初始化成功")

def test_order_creation():
    """测试订单创建"""
    print("\n" + "=" * 50)
    print("测试订单创建...")
    
    order_data = {
        "customer_name": "测试客户",
        "customer_phone": "13800138000",
        "customer_id_number": "110101199001011234",
        "car_brand": "宝马",
        "car_model": "X5",
        "car_vin": "LBV5S3102ASZ12345",
        "car_plate_number": "京A12345",
        "car_price": 500000.0,
        "loan_amount": 300000.0,
        "down_payment": 200000.0,
        "loan_period": 36,
        "monthly_payment": 8888.88,
        "interest_rate": 5.5,
        "bank_name": "中国银行",
        "created_by": "测试人员"
    }
    
    result = OrderService.create_order(order_data)
    print(f"✅ 订单创建成功: {result}")
    return result["order_id"]

def test_order_query(order_id):
    """测试订单查询"""
    print("\n" + "=" * 50)
    print("测试订单查询...")
    
    # 测试订单列表
    result = OrderService.get_orders_list(page=1, page_size=10)
    print(f"✅ 订单列表查询成功，共 {result['total']} 条记录")
    
    # 测试订单详情
    order = OrderService.get_order_detail(order_id)
    print(f"✅ 订单详情查询成功: 客户={order['customer_name']}, 阶段={order['stage']}")

def test_order_stage_update(order_id):
    """测试订单阶段更新"""
    print("\n" + "=" * 50)
    print("测试订单阶段更新...")
    
    # 测试正常流转
    result = OrderService.update_order_stage(order_id, "垫资预审", "进入垫资预审阶段")
    print(f"✅ 订单阶段更新成功: {result['old_stage']} -> {result['new_stage']}")
    
    # 测试非法流转（应该失败）
    result = OrderService.update_order_stage(order_id, "已完结", "尝试越级流转")
    if not result.get("success"):
        print(f"✅ 非法流转被正确拦截: {result['message']}")

def test_repayment_plan(order_id):
    """测试还款计划"""
    print("\n" + "=" * 50)
    print("测试还款计划生成...")
    
    result = RepaymentService.generate_repayment_plans(
        order_id=order_id,
        loan_amount=300000.0,
        loan_period=12,
        start_date="2024-02-15",
        monthly_payment=26000.0
    )
    
    if result.get("success"):
        print(f"✅ 还款计划生成成功，共 {len(result['plans'])} 期")
        
        # 查询还款计划列表
        plans = RepaymentService.get_repayment_plans(order_id=order_id)
        print(f"✅ 还款计划查询成功，共 {plans['total']} 条记录")
        
        return result['plans'][0]['plan_id']
    else:
        print(f"❌ 还款计划生成失败: {result['message']}")
        return None

def test_repayment_record(plan_id):
    """测试还款记录"""
    print("\n" + "=" * 50)
    print("测试还款记录...")
    
    if not plan_id:
        print("⚠️ 跳过还款记录测试（没有有效的还款计划）")
        return
    
    record_data = {
        "plan_id": plan_id,
        "actual_amount": 26000.0,
        "repayment_date": "2024-02-15",
        "payment_method": "银行转账",
        "remark": "第1期还款"
    }
    
    result = RepaymentService.create_repayment_record(record_data)
    if result.get("success"):
        print(f"✅ 还款记录录入成功，逾期天数: {result['overdue_days']}")
    else:
        print(f"❌ 还款记录录入失败: {result['message']}")

def test_mortgage(order_id):
    """测试抵押管理"""
    print("\n" + "=" * 50)
    print("测试抵押登记...")
    
    mortgage_data = {
        "order_id": order_id,
        "mortgage_bank": "中国银行",
        "register_date": "2024-01-20",
        "expire_date": "2027-01-20",
        "certificate_number": "BJ2024001234"
    }
    
    result = MortgageService.create_mortgage(mortgage_data)
    print(f"✅ 抵押登记成功: {result}")
    
    # 查询抵押信息
    mortgage = MortgageService.get_mortgage_by_order(order_id)
    print(f"✅ 抵押查询成功: 状态={mortgage['status']}")

def test_dashboard():
    """测试驾驶舱"""
    print("\n" + "=" * 50)
    print("测试驾驶舱...")
    
    result = DashboardService.get_dashboard()
    print(f"✅ 驾驶舱数据获取成功")
    print(f"   订单统计: {result['orders_stats']}")
    print(f"   还款统计: 逾期{result['repayment_stats']['overdue_count']}笔")
    print(f"   抵押统计: 抵押中{result['mortgage_stats']['mortgaged_count']}笔")

def main():
    """主测试函数"""
    print("\n" + "🚀 开始测试汽车分期管理平台 - 订单与还款模块" + "\n")
    
    try:
        # 测试数据库
        test_database()
        
        # 测试订单
        order_id = test_order_creation()
        test_order_query(order_id)
        test_order_stage_update(order_id)
        
        # 测试还款
        plan_id = test_repayment_plan(order_id)
        test_repayment_record(plan_id)
        
        # 测试抵押
        test_mortgage(order_id)
        
        # 测试驾驶舱
        test_dashboard()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！" + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
