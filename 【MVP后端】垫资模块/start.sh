#!/bin/bash
# 垫资管理模块启动脚本

echo "🚀 启动垫资管理模块 API 服务..."
echo ""
echo "📖 API 文档地址:"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc:      http://localhost:8000/redoc"
echo ""
echo "💡 按 Ctrl+C 停止服务"
echo ""

# 检查是否安装了依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  检测到未安装依赖，正在安装..."
    pip3 install -r requirements.txt
fi

# 启动服务
python3 main.py
