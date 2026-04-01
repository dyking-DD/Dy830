#!/bin/bash

# 飞书小程序API测试脚本

echo "=================================="
echo "飞书小程序API测试"
echo "=================================="
echo ""

# 测试1：获取统计数据
echo "📊 测试1: 获取统计数据"
curl -s http://localhost:3000/api/statistics | jq '.'
echo ""

# 测试2：提交报单
echo "📝 测试2: 提交报单"
curl -s -X POST http://localhost:3000/api/loan-application \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD'$(date +%s%N)'",
    "name": "测试客户",
    "phone": "13800138000",
    "idCard": "610123199001011234",
    "salesperson": "张业务员",
    "carModel": "奥迪A4",
    "carPrice": "25",
    "downPayment": "5",
    "loanAmount": "20",
    "loanTerm": "36",
    "notes": "测试报单"
  }' | jq '.'
echo ""

# 测试3：获取业务员报单列表
echo "📋 测试3: 获取业务员报单列表"
curl -s "http://localhost:3000/api/my-orders?salesperson=张业务员" | jq '.'
echo ""

# 测试4：获取所有报单
echo "📊 测试4: 获取所有报单（管理员）"
curl -s http://localhost:3000/api/all-orders | jq '.'
echo ""

# 测试5：审批报单（先获取一个订单ID）
echo "✅ 测试5: 审批报单"
ORDER_ID=$(curl -s "http://localhost:3000/api/my-orders?salesperson=张业务员" | jq -r '.orders[0].order_id')
echo "订单ID: $ORDER_ID"

if [ "$ORDER_ID" != "null" ]; then
  curl -s -X POST http://localhost:3000/api/approve-order \
    -H "Content-Type: application/json" \
    -d "{
      \"orderId\": \"$ORDER_ID\",
      \"status\": \"approved\",
      \"riskLevel\": \"low\",
      \"remarks\": \"测试审批通过\",
      \"approver\": \"管理员\"
    }" | jq '.'
  echo ""

  # 验证审批结果
  echo "🔍 验证审批结果"
  curl -s "http://localhost:3000/api/order/$ORDER_ID" | jq '.'
else
  echo "❌ 没有找到订单"
fi

echo ""
echo "=================================="
echo "测试完成！"
echo "=================================="