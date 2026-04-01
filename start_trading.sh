#!/bin/bash
# Mac模拟交易系统启动脚本

echo "🎯 Mac模拟交易系统 - 安装依赖并启动"
echo ""

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python3"
    echo "   推荐: brew install python3"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
python3 -m pip install aiohttp aiohttp-cors --quiet

# 启动服务器
echo "🚀 启动交易系统..."
echo ""
cd "$(dirname "$0")"
python3 trading_server.py
