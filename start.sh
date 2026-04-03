#!/bin/bash
# 汽车分期智能管理平台 - 一键启动脚本

cd "$(dirname "$0")"

echo "======================================"
echo "🚗 汽车分期智能管理平台"
echo "======================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt --quiet 2>/dev/null

# 启动服务
echo ""
echo "🚀 启动服务..."
echo "📖 API 文档: http://localhost:8899/docs"
echo "📖 ReDoc 文档: http://localhost:8899/redoc"
echo ""
echo "🔐 认证信息："
echo "  后台管理员：admin / admin123"
echo "  前台客户：手机号 13800138001 / 密码 123456"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py
