#!/bin/bash

# GPS管理模块启动脚本

echo "=========================================="
echo "🚀 启动GPS管理模块..."
echo "=========================================="

# 进入脚本目录
cd "$(dirname "$0")"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -r requirements.txt -q

# 启动服务
echo "🌟 启动服务..."
echo "📖 API文档: http://localhost:8001/docs"
echo "📖 ReDoc文档: http://localhost:8001/redoc"
echo "=========================================="

python3 main.py
