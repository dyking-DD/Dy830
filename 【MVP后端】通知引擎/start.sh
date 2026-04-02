#!/bin/bash
# 快速启动脚本

echo ""
echo "============================================================"
echo "🚀 汽车分期管理平台 - 通知引擎"
echo "============================================================"
echo ""

# 检查Python版本
echo "📌 检查Python版本..."
python3 --version

# 检查并安装依赖
echo ""
echo "📌 检查依赖包..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  依赖包未安装，正在安装..."
    pip3 install -r requirements.txt
else
    echo "✅ 依赖包已安装"
fi

echo ""
echo "============================================================"
echo "🎯 启动服务..."
echo "============================================================"
echo ""
echo "📍 API文档: http://localhost:8000/docs"
echo "📍 ReDoc文档: http://localhost:8000/redoc"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

# 启动服务
python3 main.py
