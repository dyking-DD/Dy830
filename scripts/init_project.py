#!/usr/bin/env python3
"""
项目初始化脚本
一键初始化数据库和基础配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import init_sqlite_db


def main():
    """初始化项目"""
    print("🚀 初始化 daily_stock_analysis 项目...")
    
    # 初始化数据库
    print("📦 初始化数据库...")
    init_sqlite_db()
    
    print("\n✅ 初始化完成！")
    print("\n下一步:")
    print("1. 配置 Tushare token: 编辑 config/tushare.yaml")
    print("2. 安装依赖: pip install -r requirements.txt")
    print("3. 运行测试: python utils/data_fetcher.py")


if __name__ == "__main__":
    main()
