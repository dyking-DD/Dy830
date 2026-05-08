#!/usr/bin/env python3
"""
TrendMatrix 回测脚本
运行完整回测 + 输出结果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.core import run_backtest, print_results

if __name__ == "__main__":
    results = run_backtest()
    print_results(results)
