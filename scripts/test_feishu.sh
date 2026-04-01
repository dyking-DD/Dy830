#!/bin/bash
# 测试飞书通知 - 加载.env配置

cd /home/gem/workspace/agent/workspace/daily_stock_analysis

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 运行测试
python3 scripts/test_notification.py