#!/bin/bash

# MASLAS 飞书小程序 - 一键启动脚本

echo "====================================="
echo "  MASLAS 飞书小程序启动脚本"
echo "====================================="
echo ""

# 检查Node.js
echo "🔍 检查Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js"
    exit 1
fi
echo "✅ Node.js版本: $(node -v)"
echo ""

# 检查MySQL
echo "🔍 检查MySQL..."
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL未安装，请先安装MySQL"
    exit 1
fi
echo "✅ MySQL已安装"
echo ""

# 进入项目目录
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"

echo "📂 项目目录: $PROJECT_DIR"
echo ""

# 检查是否已安装依赖
echo "🔍 检查依赖..."
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
    echo ""
fi
echo "✅ 依赖已安装"
echo ""

# 初始化数据库
echo "🔍 检查数据库..."
read -p "是否初始化数据库？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗄️  初始化数据库..."
    mysql -u root -p < "$PROJECT_DIR/../database_init.sql"
    echo "✅ 数据库初始化完成"
    echo ""
fi

# 启动服务器
echo "🚀 启动服务器..."
echo ""
echo "====================================="
echo "  服务器启动成功！"
echo "====================================="
echo ""
echo "📡 服务器地址: http://localhost:3000"
echo "📱 报单表单: http://localhost:3000/feishu-app/loan-form.html"
echo "📋 我的报单: http://localhost:3000/feishu-app/my-orders.html"
echo "📊 控制面板: http://localhost:3000/dashboard.html"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "====================================="
echo ""

# 启动API服务器
node "$PROJECT_DIR/../api-server-full.js"
