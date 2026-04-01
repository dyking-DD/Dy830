#!/usr/bin/env python3
"""
历史数据批量下载脚本
"""
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_fetcher import DataFetcher


def main():
    parser = argparse.ArgumentParser(description='下载A股历史数据')
    parser.add_argument('--limit', type=int, default=100, 
                        help='下载股票数量 (默认100只)')
    parser.add_argument('--start', type=str, default='20200101',
                        help='起始日期 (YYYYMMDD)')
    args = parser.parse_args()
    
    print(f"🚀 开始下载历史数据...")
    print(f"   股票数量: {args.limit}")
    print(f"   起始日期: {args.start}")
    
    fetcher = DataFetcher()
    
    # 获取股票列表
    stocks = fetcher.get_stock_list()
    stock_codes = stocks['ts_code'].head(args.limit).tolist()
    
    print(f"\n📊 准备下载 {len(stock_codes)} 只股票数据...")
    
    # 批量下载
    fetcher.download_history_batch(stock_codes, args.start)
    
    print("\n✅ 下载完成！")
    print(f"数据保存在: data/raw/daily/")


if __name__ == "__main__":
    main()
