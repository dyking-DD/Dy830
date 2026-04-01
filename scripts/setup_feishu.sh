#!/bin/bash
# 配置飞书机器人Webhook

CONFIG_FILE=".env"

echo "========================================"
echo "飞书机器人配置"
echo "========================================"
echo ""
echo "配置步骤："
echo "1. 在飞书群聊中，点击右上角 '...' → 设置 → 群机器人"
echo "2. 点击 '添加机器人' → 选择 '自定义机器人'"
echo "3. 给机器人起个名字（如：量化交易助手）"
echo "4. 复制Webhook地址"
echo ""
echo "Webhook地址格式："
echo "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx"
echo ""

# 检查现有配置
if [ -f "$CONFIG_FILE" ]; then
    echo "发现已有配置："
    grep "FEISHU_WEBHOOK" "$CONFIG_FILE" 2>/dev/null || echo "（未配置）"
    echo ""
fi

read -p "请输入Webhook地址（或按Enter跳过）: " webhook

if [ -n "$webhook" ]; then
    # 保存配置
    echo "FEISHU_WEBHOOK=$webhook" > "$CONFIG_FILE"
    echo ""
    echo "✓ 配置已保存到 $CONFIG_FILE"
    echo ""
    
    # 测试发送
    read -p "是否发送测试消息？ (y/n): " test_send
    if [ "$test_send" = "y" ] || [ "$test_send" = "Y" ]; then
        echo ""
        echo "正在发送测试消息..."
        python3 << EOF
import requests
import json

webhook = "$webhook"
message = {
    "msg_type": "text",
    "content": {
        "text": "🦞 量化交易系统测试消息\n\n配置成功！以后每天收盘后会自动推送交易日报。"
    }
}

try:
    response = requests.post(webhook, json=message, timeout=10)
    result = response.json()
    if result.get("code") == 0:
        print("✓ 测试消息发送成功！请检查飞书群聊。")
    else:
        print(f"✗ 发送失败: {result.get('msg')}")
except Exception as e:
    print(f"✗ 发送失败: {e}")
EOF
    fi
else
    echo "跳过配置"
fi

echo ""
echo "========================================"
echo "配置完成"
echo "========================================"
echo ""
echo "使用方式："
echo "1. 环境变量: export FEISHU_WEBHOOK=你的地址"
echo "2. 命令行: python3 scripts/daily_scanner.py --webhook 你的地址"
echo "3. 加载配置: source .env && python3 scripts/daily_scanner.py"
echo ""
